from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
import json
import math
import os
from pathlib import Path
from statistics import pstdev
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from openai import OpenAI

from .cohort import load_cohort
from .protocol import PROTOCOL_V1

NY = ZoneInfo("America/New_York")
DATA_BASE = "https://data.alpaca.markets"
PROMPT_PATH = Path("prompts/replay_professional_v2.md")
REPLAY_V2_DIR = Path("data/replay_v2")


def _headers() -> dict[str, str]:
    key = os.environ.get("ALPACA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY")
    secret = os.environ.get("ALPACA_API_SECRET_KEY") or os.environ.get("ALPACA_API_SECRET")
    if not key or not secret:
        raise RuntimeError("Alpaca credentials are required")
    return {
        "APCA-API-KEY-ID": key,
        "APCA-API-SECRET-KEY": secret,
        "Accept": "application/json",
    }


def _get_json(url: str) -> dict[str, Any]:
    request = Request(url=url, headers=_headers(), method="GET")
    with urlopen(request, timeout=30) as response:  # nosec B310: fixed Alpaca HTTPS base
        return json.loads(response.read().decode("utf-8"))


def _cutoff_at(day: str) -> str:
    local = datetime.combine(date.fromisoformat(day), time(16, 5), tzinfo=NY)
    return local.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _daily_bars(symbol: str, *, start: datetime, end: datetime) -> list[dict[str, Any]]:
    params = urlencode({
        "timeframe": "1Day",
        "start": start.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end": end.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "limit": "10000",
        "adjustment": "raw",
        "feed": "iex",
        "sort": "asc",
    })
    payload = _get_json(f"{DATA_BASE}/v2/stocks/{symbol}/bars?{params}")
    bars = payload.get("bars")
    if not isinstance(bars, list):
        raise RuntimeError(f"missing daily bars for {symbol}")
    out: list[dict[str, Any]] = []
    for row in bars:
        if not isinstance(row, dict) or not isinstance(row.get("t"), str):
            continue
        dt = datetime.fromisoformat(row["t"].replace("Z", "+00:00")).astimezone(NY)
        out.append({
            "date": dt.date().isoformat(),
            "open": float(row["o"]),
            "high": float(row["h"]),
            "low": float(row["l"]),
            "close": float(row["c"]),
            "volume": float(row["v"]),
        })
    return out


def _historical_news(symbols: tuple[str, ...], *, cutoff_day: str, lookback_days: int = 14) -> list[dict[str, Any]]:
    cutoff = datetime.fromisoformat(_cutoff_at(cutoff_day).replace("Z", "+00:00"))
    start = cutoff - timedelta(days=lookback_days)
    params = urlencode({
        "start": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end": cutoff.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "symbols": ",".join(symbols),
        "limit": "50",
        "sort": "desc",
        "include_content": "false",
    })
    try:
        payload = _get_json(f"{DATA_BASE}/v1beta1/news?{params}")
    except Exception:
        return []
    rows = payload.get("news")
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        created = row.get("created_at") or row.get("updated_at")
        if not isinstance(created, str):
            continue
        created_dt = datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(timezone.utc)
        if created_dt > cutoff:
            continue
        url = row.get("url")
        headline = row.get("headline")
        if not isinstance(url, str) or not isinstance(headline, str):
            continue
        out.append({
            "headline": headline,
            "summary": str(row.get("summary") or ""),
            "source": str(row.get("source") or "Alpaca News"),
            "url": url,
            "published_at": created_dt.isoformat(timespec="seconds").replace("+00:00", "Z"),
            "symbols": [str(x) for x in (row.get("symbols") or []) if isinstance(x, str)],
        })
    return out


def _pct_change(rows: list[dict[str, Any]], sessions: int) -> float | None:
    if len(rows) <= sessions:
        return None
    start = rows[-sessions - 1]["close"]
    end = rows[-1]["close"]
    return ((end / start) - 1.0) * 100.0


def _sma(rows: list[dict[str, Any]], sessions: int) -> float | None:
    if len(rows) < sessions:
        return None
    values = [row["close"] for row in rows[-sessions:]]
    return sum(values) / len(values)


def _annualized_volatility(rows: list[dict[str, Any]], sessions: int = 60) -> float | None:
    recent = rows[-(sessions + 1):]
    if len(recent) < 3:
        return None
    returns = []
    for left, right in zip(recent[:-1], recent[1:]):
        if left["close"] <= 0:
            continue
        returns.append((right["close"] / left["close"]) - 1.0)
    if len(returns) < 2:
        return None
    return pstdev(returns) * math.sqrt(252.0) * 100.0


def _max_drawdown(rows: list[dict[str, Any]], sessions: int = 252) -> float | None:
    recent = rows[-sessions:]
    if not recent:
        return None
    peak = recent[0]["close"]
    worst = 0.0
    for row in recent:
        peak = max(peak, row["close"])
        dd = ((row["close"] / peak) - 1.0) * 100.0
        worst = min(worst, dd)
    return worst


def _volume_ratio(rows: list[dict[str, Any]]) -> float | None:
    if len(rows) < 21:
        return None
    baseline = [row["volume"] for row in rows[-21:-1]]
    mean = sum(baseline) / len(baseline) if baseline else 0.0
    return rows[-1]["volume"] / mean if mean > 0 else None


def _levels(rows: list[dict[str, Any]], sessions: int = 60) -> dict[str, float | None]:
    recent = rows[-sessions:]
    if not recent:
        return {"support": None, "resistance": None}
    return {
        "support": min(row["low"] for row in recent),
        "resistance": max(row["high"] for row in recent),
    }


def _technical_summary(rows: list[dict[str, Any]], spy_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("rows cannot be empty")
    sma20 = _sma(rows, 20)
    sma50 = _sma(rows, 50)
    sma200 = _sma(rows, 200)
    price = rows[-1]["close"]
    ret20 = _pct_change(rows, 20)
    spy20 = _pct_change(spy_rows, 20)
    levels = _levels(rows)
    trend = "mixed"
    if sma20 and sma50 and sma200:
        if price > sma20 > sma50 > sma200:
            trend = "strong_uptrend"
        elif price < sma20 < sma50 < sma200:
            trend = "strong_downtrend"
        elif price > sma50:
            trend = "uptrend_or_recovery"
        elif price < sma50:
            trend = "downtrend_or_weakness"
    return {
        "last_price": price,
        "returns_pct": {
            "5d": _pct_change(rows, 5),
            "20d": ret20,
            "60d": _pct_change(rows, 60),
            "252d": _pct_change(rows, 252),
        },
        "sma": {"20": sma20, "50": sma50, "200": sma200},
        "trend": trend,
        "annualized_volatility_60d_pct": _annualized_volatility(rows, 60),
        "max_drawdown_252d_pct": _max_drawdown(rows, 252),
        "volume_vs_20d_average": _volume_ratio(rows),
        "support_60d": levels["support"],
        "resistance_60d": levels["resistance"],
        "relative_strength_vs_spy_20d_pct": None if ret20 is None or spy20 is None else ret20 - spy20,
        "history_sessions_available": len(rows),
    }


def _selection_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["selected_symbol", "market_regime", "shortlist", "selection_summary", "why_not_others"],
        "properties": {
            "selected_symbol": {"type": ["string", "null"]},
            "market_regime": {"type": "string"},
            "shortlist": {
                "type": "array",
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["symbol", "score", "reason"],
                    "properties": {
                        "symbol": {"type": "string"},
                        "score": {"type": "number", "minimum": 0, "maximum": 1},
                        "reason": {"type": "string"},
                    },
                },
            },
            "selection_summary": {"type": "string"},
            "why_not_others": {"type": "string"},
        },
    }


def _decision_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "action", "symbol", "notional_eur", "confidence", "horizon_days", "stop_pct", "target_price",
            "short_answer", "thesis", "counter_thesis", "chart_reading", "news_reading", "risk_lesson",
            "support_levels", "resistance_levels", "sources",
        ],
        "properties": {
            "action": {"type": "string", "enum": ["BUY", "NO_TRADE"]},
            "symbol": {"type": ["string", "null"]},
            "notional_eur": {"type": "number", "minimum": 0, "maximum": 150},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "horizon_days": {"type": "integer", "minimum": 0, "maximum": 10},
            "stop_pct": {"type": ["number", "null"]},
            "target_price": {"type": ["number", "null"]},
            "short_answer": {"type": "string"},
            "thesis": {"type": "string"},
            "counter_thesis": {"type": "string"},
            "chart_reading": {"type": "string"},
            "news_reading": {"type": "string"},
            "risk_lesson": {"type": "string"},
            "support_levels": {"type": "array", "items": {"type": "number"}},
            "resistance_levels": {"type": "array", "items": {"type": "number"}},
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["url", "published_at", "label"],
                    "properties": {
                        "url": {"type": "string"},
                        "published_at": {"type": ["string", "null"]},
                        "label": {"type": "string"},
                    },
                },
            },
        },
    }


def _follow_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["action", "confidence", "thesis_status", "new_information", "reason"],
        "properties": {
            "action": {"type": "string", "enum": ["HOLD", "SELL"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "thesis_status": {"type": "string"},
            "new_information": {"type": "string"},
            "reason": {"type": "string"},
        },
    }


def _structured_call(*, model: str, name: str, schema: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    client = OpenAI(api_key=api_key, timeout=60.0, max_retries=2)
    response = client.responses.create(
        model=model,
        instructions=PROMPT_PATH.read_text(encoding="utf-8"),
        input=json.dumps(payload, sort_keys=True, ensure_ascii=False),
        text={"format": {"type": "json_schema", "name": name, "strict": True, "schema": schema}},
        store=False,
        metadata={"component": "ai-trading-forward-lab", "replay_version": "professional-v2"},
    )
    if getattr(response, "status", None) not in (None, "completed"):
        raise RuntimeError(f"OpenAI response status={getattr(response, 'status', None)}")
    text = getattr(response, "output_text", None)
    if not isinstance(text, str) or not text.strip():
        raise RuntimeError("OpenAI response has no output_text")
    return json.loads(text)


def _news_for_symbol(news: list[dict[str, Any]], symbol: str, *, limit: int = 8) -> list[dict[str, Any]]:
    selected = [row for row in news if not row["symbols"] or symbol in row["symbols"]]
    return selected[:limit]


def _validate_sources(decision: dict[str, Any], news: list[dict[str, Any]], cutoff_at: str) -> None:
    cutoff = datetime.fromisoformat(cutoff_at.replace("Z", "+00:00"))
    allowed = {row["url"] for row in news}
    for source in decision.get("sources", []):
        if source["url"] not in allowed:
            raise RuntimeError("decision cited source outside supplied historical evidence")
        published = source.get("published_at")
        if published:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            if dt > cutoff:
                raise RuntimeError("post-cutoff source detected")


def _chart_payload(rows: list[dict[str, Any]], *, cutoff_day: str) -> list[dict[str, Any]]:
    eligible = [row for row in rows if row["date"] <= cutoff_day]
    return eligible[-520:]


def _post_cutoff_payload(rows: list[dict[str, Any]], *, cutoff_day: str, sessions: int = 15) -> list[dict[str, Any]]:
    future = [row for row in rows if row["date"] > cutoff_day]
    return future[:sessions]


def _simulate_entry_and_exit(
    decision: dict[str, Any],
    rows: list[dict[str, Any]],
    *,
    cutoff_day: str,
    exit_day: str | None,
) -> dict[str, Any]:
    if decision["action"] != "BUY":
        return {"available": True, "net_pnl_eur": 0.0, "entry_day": None, "exit_day": None}
    future = [row for row in rows if row["date"] > cutoff_day]
    if not future:
        return {"available": False}
    entry_row = future[0]
    target_exit = next((row for row in future if row["date"] == exit_day), future[min(len(future) - 1, max(1, decision["horizon_days"] - 1))])
    slip = 5.0 / 10000.0
    fee = 5.0 / 10000.0
    entry = entry_row["open"] * (1 + slip)
    exit_price = target_exit["close"] * (1 - slip)
    shares = decision["notional_eur"] / entry
    gross = shares * (exit_price - entry)
    costs = decision["notional_eur"] * fee * 2
    net = gross - costs
    return {
        "available": True,
        "entry_day": entry_row["date"],
        "entry_price": entry,
        "exit_day": target_exit["date"],
        "exit_price": exit_price,
        "shares_simulated": shares,
        "net_pnl_eur": net,
        "return_pct": (net / decision["notional_eur"]) * 100.0,
        "capital_after_eur": 1000.0 + net,
    }


def build_professional_replay(cutoff_day: str, *, all_bars: dict[str, list[dict[str, Any]]], news: list[dict[str, Any]]) -> dict[str, Any]:
    cohort = load_cohort()
    cutoff_at = _cutoff_at(cutoff_day)
    spy_rows = [row for row in all_bars[PROTOCOL_V1.benchmark_symbol] if row["date"] <= cutoff_day]
    universe_summary: dict[str, Any] = {}
    for symbol in PROTOCOL_V1.tradable_universe:
        rows = [row for row in all_bars[symbol] if row["date"] <= cutoff_day]
        universe_summary[symbol] = _technical_summary(rows, spy_rows)

    selection = _structured_call(
        model=cohort.model,
        name="market_selection_v2",
        schema=_selection_schema(),
        payload={
            "stage": "market_selection",
            "cutoff_at": cutoff_at,
            "protocol": asdict(PROTOCOL_V1),
            "universe_summary": universe_summary,
            "news": news[:30],
        },
    )
    selected = selection.get("selected_symbol")
    if selected is not None and selected not in PROTOCOL_V1.tradable_universe:
        raise RuntimeError("market scan selected symbol outside universe")

    if selected is None:
        decision = {
            "action": "NO_TRADE", "symbol": None, "notional_eur": 0.0, "confidence": 0.0,
            "horizon_days": 0, "stop_pct": None, "target_price": None,
            "short_answer": "No trade: no setup cleared the quality threshold.",
            "thesis": selection.get("selection_summary", "No sufficiently clear setup."),
            "counter_thesis": "A stronger setup may appear in a later session.",
            "chart_reading": "No single chart justified capital allocation.",
            "news_reading": "No evidence changed the no-trade conclusion.",
            "risk_lesson": "Not trading is a valid risk-management decision.",
            "support_levels": [], "resistance_levels": [], "sources": [],
        }
        selected_rows: list[dict[str, Any]] = []
        selected_news: list[dict[str, Any]] = []
    else:
        selected_rows = [row for row in all_bars[selected] if row["date"] <= cutoff_day]
        selected_news = _news_for_symbol(news, selected)
        decision = _structured_call(
            model=cohort.model,
            name="professional_trade_decision_v2",
            schema=_decision_schema(),
            payload={
                "stage": "trade_decision",
                "cutoff_at": cutoff_at,
                "selected_symbol": selected,
                "selection": selection,
                "portfolio": {"cash_eur": 1000.0, "equity_eur": 1000.0, "positions": {}},
                "protocol": asdict(PROTOCOL_V1),
                "selected_asset_full_daily_history": selected_rows,
                "selected_asset_summary": universe_summary[selected],
                "spy_summary": _technical_summary(spy_rows, spy_rows),
                "news": selected_news,
            },
        )
        if decision["action"] == "BUY" and decision["symbol"] != selected:
            raise RuntimeError("decision symbol differs from explicit market selection")
        if decision["action"] == "NO_TRADE":
            decision["symbol"] = None
            decision["notional_eur"] = 0.0
            decision["horizon_days"] = 0
            decision["stop_pct"] = None
            decision["target_price"] = None
        _validate_sources(decision, selected_news, cutoff_at)

    lifecycle: list[dict[str, Any]] = []
    exit_day: str | None = None
    if decision["action"] == "BUY" and selected:
        future_rows = [row for row in all_bars[selected] if row["date"] > cutoff_day]
        max_follow = min(len(future_rows), max(1, decision["horizon_days"]))
        initial_entry = future_rows[0]["open"] if future_rows else None
        for index, row in enumerate(future_rows[:max_follow], start=1):
            day = row["date"]
            bars_until_day = [r for r in all_bars[selected] if r["date"] <= day]
            day_news_all = _historical_news((selected,), cutoff_day=day, lookback_days=3)
            day_news = [n for n in day_news_all if n["published_at"] > cutoff_at]
            follow = _structured_call(
                model=cohort.model,
                name="position_follow_v2",
                schema=_follow_schema(),
                payload={
                    "stage": "position_follow",
                    "original_cutoff_at": cutoff_at,
                    "current_cutoff_at": _cutoff_at(day),
                    "original_decision": decision,
                    "entry_price_raw": initial_entry,
                    "days_since_entry": index,
                    "selected_asset_history_to_current_day": bars_until_day[-260:],
                    "new_news_since_original_cutoff": day_news[:8],
                    "previous_assessments": lifecycle,
                },
            )
            lifecycle.append({"date": day, **follow})
            if follow["action"] == "SELL":
                exit_day = day
                break
        if exit_day is None and future_rows:
            exit_day = future_rows[min(len(future_rows) - 1, max_follow - 1)]["date"]

    result = _simulate_entry_and_exit(
        decision,
        all_bars[selected] if selected else [],
        cutoff_day=cutoff_day,
        exit_day=exit_day,
    )

    spy_future = _post_cutoff_payload(all_bars[PROTOCOL_V1.benchmark_symbol], cutoff_day=cutoff_day, sessions=15)
    if result.get("available") and result.get("entry_day") and result.get("exit_day"):
        try:
            b0 = next(r for r in all_bars[PROTOCOL_V1.benchmark_symbol] if r["date"] == result["entry_day"])["open"]
            b1 = next(r for r in all_bars[PROTOCOL_V1.benchmark_symbol] if r["date"] == result["exit_day"])["close"]
            result["spy_return_pct"] = ((b1 / b0) - 1.0) * 100.0
        except StopIteration:
            result["spy_return_pct"] = None

    chart = {
        "symbol": selected,
        "candles_before_cutoff": _chart_payload(all_bars[selected], cutoff_day=cutoff_day) if selected else [],
        "candles_after_cutoff": _post_cutoff_payload(all_bars[selected], cutoff_day=cutoff_day, sessions=15) if selected else [],
        "spy_before_cutoff": _chart_payload(all_bars[PROTOCOL_V1.benchmark_symbol], cutoff_day=cutoff_day),
        "spy_after_cutoff": spy_future,
        "overlays": {
            "sma20": universe_summary[selected]["sma"]["20"] if selected else None,
            "sma50": universe_summary[selected]["sma"]["50"] if selected else None,
            "sma200": universe_summary[selected]["sma"]["200"] if selected else None,
            "support_levels": decision.get("support_levels", []),
            "resistance_levels": decision.get("resistance_levels", []),
            "target_price": decision.get("target_price"),
            "stop_pct": decision.get("stop_pct"),
        },
    }

    return {
        "replay_id": f"professional-{cutoff_day}",
        "version": "professional-v2",
        "cutoff_date": cutoff_day,
        "cutoff_at": cutoff_at,
        "blind": True,
        "analysis_scope": {
            "universe_size": len(PROTOCOL_V1.tradable_universe),
            "daily_history_target": "~2 years per symbol when available",
            "technical_horizons": ["5d", "20d", "60d", "252d"],
            "news_lookback_days": 14,
            "ui_viewport_is_not_model_context": True,
        },
        "selection": selection,
        "decision": decision,
        "lifecycle": lifecycle,
        "result": result,
        "chart": chart,
        "evidence": selected_news if selected else news[:8],
    }


def generate_professional_replays(*, count: int = 3) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=760)
    end = now + timedelta(days=30)
    symbols = tuple((*PROTOCOL_V1.tradable_universe, PROTOCOL_V1.benchmark_symbol))
    all_bars = {symbol: _daily_bars(symbol, start=start, end=end) for symbol in symbols}
    sessions = [row["date"] for row in all_bars[PROTOCOL_V1.benchmark_symbol]]
    if len(sessions) < count + 10:
        raise RuntimeError("not enough historical sessions")
    # Avoid the very latest sessions so lifecycle/reveal has actual future data available.
    replay_days = sessions[-(count + 8):-8]
    out: list[dict[str, Any]] = []
    for replay_day in replay_days:
        news = _historical_news(tuple(PROTOCOL_V1.tradable_universe), cutoff_day=replay_day, lookback_days=14)
        out.append(build_professional_replay(replay_day, all_bars=all_bars, news=news))
    payload = {
        "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "simulation_only": True,
        "forward_ledger_untouched": True,
        "version": "professional-v2",
        "replay_count": len(out),
        "sessions": out,
    }
    REPLAY_V2_DIR.mkdir(parents=True, exist_ok=True)
    (REPLAY_V2_DIR / "index.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    payload = generate_professional_replays()
    print(f"generated_professional_replays={payload['replay_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
