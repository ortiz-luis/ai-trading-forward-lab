from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime, time, timedelta, timezone
import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from .cohort import load_cohort
from .decision_contract import DecisionInput
from .protocol import PROTOCOL_V1
from .providers.openai_decision import OpenAIDecisionProvider
from .schemas import Action

NY = ZoneInfo("America/New_York")
DATA_BASE = "https://data.alpaca.markets"
REPLAY_DIR = Path("data/replay")
PROMPT_PATH = Path("prompts/trading_v1.md")


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
    with urlopen(request, timeout=20) as response:  # nosec B310: fixed Alpaca HTTPS base
        return json.loads(response.read().decode("utf-8"))


def _daily_bars(symbol: str, *, start: datetime, end: datetime) -> list[dict[str, Any]]:
    params = urlencode({
        "timeframe": "1Day",
        "start": start.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "end": end.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "limit": "1000",
        "adjustment": "raw",
        "feed": "iex",
        "sort": "asc",
    })
    payload = _get_json(f"{DATA_BASE}/v2/stocks/{symbol}/bars?{params}")
    bars = payload.get("bars")
    if not isinstance(bars, list):
        raise RuntimeError(f"missing daily bars for {symbol}")
    cleaned: list[dict[str, Any]] = []
    for row in bars:
        if not isinstance(row, dict) or not isinstance(row.get("t"), str):
            continue
        dt = datetime.fromisoformat(row["t"].replace("Z", "+00:00")).astimezone(NY)
        cleaned.append({
            "date": dt.date().isoformat(),
            "open": float(row["o"]),
            "high": float(row["h"]),
            "low": float(row["l"]),
            "close": float(row["c"]),
            "volume": float(row["v"]),
        })
    return cleaned


def _cutoff_at(day: str) -> str:
    local = datetime.combine(date.fromisoformat(day), time(16, 5), tzinfo=NY)
    return local.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _chart(rows: list[dict[str, Any]], cutoff_day: str, *, limit: int = 22) -> list[dict[str, Any]]:
    eligible = [row for row in rows if row["date"] <= cutoff_day]
    return [{"date": row["date"], "close": row["close"]} for row in eligible[-limit:]]


def _market_context(all_bars: dict[str, list[dict[str, Any]]], cutoff_day: str) -> tuple[dict[str, Any], dict[str, Any]]:
    market: dict[str, Any] = {}
    charts: dict[str, Any] = {}
    cutoff = _cutoff_at(cutoff_day)
    for symbol, rows in all_bars.items():
        eligible = [row for row in rows if row["date"] <= cutoff_day]
        if not eligible:
            raise RuntimeError(f"no bars available for {symbol} at {cutoff_day}")
        recent = eligible[-20:]
        last = recent[-1]
        market[symbol] = {
            "price": last["close"],
            "currency": "USD",
            "observed_at": cutoff,
            "recent_daily_bars": recent,
        }
        charts[symbol] = _chart(rows, cutoff_day)
    return market, charts


def _decision_payload(cutoff_day: str, market: dict[str, Any], charts: dict[str, Any]) -> dict[str, Any]:
    cohort = load_cohort()
    cutoff = _cutoff_at(cutoff_day)
    evidence = [{
        "url": "https://data.alpaca.markets/v2/stocks/bars",
        "published_at": cutoff,
        "source_name": "Alpaca Market Data",
        "summary": "Daily OHLCV data available no later than the replay cutoff.",
    }]
    input_data = DecisionInput(
        cutoff_at=cutoff,
        portfolio={
            "starting_capital_eur": 1000.0,
            "cash_eur": 1000.0,
            "equity_eur": 1000.0,
            "positions": {},
            "replay_mode": True,
        },
        protocol=asdict(PROTOCOL_V1),
        market=market,
        evidence=evidence,
        model_identifier=cohort.model,
    )
    instructions = PROMPT_PATH.read_text(encoding="utf-8") + (
        "\n\nHistorical replay guard: pretend cutoff_at is the present moment. "
        "You have zero open positions, so only BUY or NO_TRADE are valid. "
        "Never use knowledge of what happened after cutoff_at."
    )
    result = OpenAIDecisionProvider(model=cohort.model).decide(input_data, instructions=instructions)
    if not result.ok or result.decision is None:
        raise RuntimeError(result.error_message or "OpenAI replay decision failed")
    decision = result.decision
    if decision.action not in {Action.BUY, Action.NO_TRADE}:
        raise RuntimeError(f"invalid replay action for empty portfolio: {decision.action}")
    if decision.action == Action.BUY:
        if decision.notional_eur > 150.0 + 1e-9:
            raise RuntimeError("replay BUY exceeds frozen 15% position limit")
        if decision.symbol not in PROTOCOL_V1.tradable_universe:
            raise RuntimeError("replay BUY symbol outside frozen universe")
    return {
        "action": decision.action.value,
        "symbol": decision.symbol,
        "notional_eur": decision.notional_eur,
        "confidence": decision.confidence,
        "horizon_days": decision.horizon_days,
        "stop_pct": decision.stop_pct,
        "thesis": decision.thesis,
        "counter_thesis": decision.counter_thesis,
        "sources": list(decision.sources),
        "model": result.model,
        "response_id": result.response_id,
        "repaired": result.repaired,
    }


def _next_day_result(
    decision: dict[str, Any],
    *,
    replay_day: str,
    next_day: str | None,
    all_bars: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    if next_day is None:
        return {"available": False, "reason": "next trading session has not happened yet"}

    spy_row = next(row for row in all_bars["SPY"] if row["date"] == next_day)
    spy_return = ((spy_row["close"] / spy_row["open"]) - 1.0) * 100.0
    if decision["action"] == "NO_TRADE":
        return {
            "available": True,
            "session_date": next_day,
            "action": "NO_TRADE",
            "entry": None,
            "close": None,
            "shares_simulated": 0.0,
            "net_pnl_eur": 0.0,
            "return_pct": 0.0,
            "benchmark_return_pct": spy_return,
        }

    symbol = decision["symbol"]
    row = next(row for row in all_bars[symbol] if row["date"] == next_day)
    slippage = 5.0 / 10000.0
    fee = 5.0 / 10000.0
    entry = row["open"] * (1.0 + slippage)
    exit_price = row["close"] * (1.0 - slippage)
    shares = decision["notional_eur"] / entry
    gross = shares * (exit_price - entry)
    costs = decision["notional_eur"] * fee * 2.0
    net = gross - costs
    return {
        "available": True,
        "session_date": next_day,
        "action": "BUY",
        "entry": entry,
        "raw_open": row["open"],
        "close": row["close"],
        "high": row["high"],
        "low": row["low"],
        "shares_simulated": shares,
        "net_pnl_eur": net,
        "return_pct": (net / decision["notional_eur"]) * 100.0,
        "benchmark_return_pct": spy_return,
    }


def generate_replays(*, count: int = 5) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=50)
    end = now + timedelta(days=1)
    symbols = tuple((*PROTOCOL_V1.tradable_universe, PROTOCOL_V1.benchmark_symbol))
    all_bars = {symbol: _daily_bars(symbol, start=start, end=end) for symbol in symbols}
    sessions = [row["date"] for row in all_bars["SPY"]]
    if len(sessions) < count:
        raise RuntimeError("not enough completed SPY sessions for replay")
    replay_days = sessions[-count:]

    sessions_out: list[dict[str, Any]] = []
    for replay_day in replay_days:
        market, charts = _market_context(all_bars, replay_day)
        decision = _decision_payload(replay_day, market, charts)
        idx = sessions.index(replay_day)
        next_day = sessions[idx + 1] if idx + 1 < len(sessions) else None
        result = _next_day_result(
            decision,
            replay_day=replay_day,
            next_day=next_day,
            all_bars=all_bars,
        )
        sessions_out.append({
            "replay_id": f"replay-{replay_day}",
            "cutoff_date": replay_day,
            "cutoff_at": _cutoff_at(replay_day),
            "next_session_date": next_day,
            "blind": True,
            "starting_capital_eur": 1000.0,
            "charts": charts,
            "decision": decision,
            "result_next_session": result,
        })

    payload = {
        "generated_at": now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "simulation_only": True,
        "forward_ledger_untouched": True,
        "replay_count": len(sessions_out),
        "sessions": sessions_out,
    }
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    (REPLAY_DIR / "index.json").write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    payload = generate_replays()
    print(f"generated_replays={payload['replay_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
