from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Callable, Sequence

from .effective_portfolio import rebuild_effective_portfolio_from_ledgers
from .evidence import EvidenceKind, EvidenceRecord, build_evidence_context, write_evidence_manifest
from .protocol import PROTOCOL_V1
from .providers.alpaca import AlpacaMarketDataProvider
from .providers.market import MarketClosed, MarketDataProvider, require_tradeable_quote


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _portfolio_payload(
    decisions_path: Path,
    evaluations_path: Path,
    starting_capital_eur: float,
) -> dict[str, object]:
    return rebuild_effective_portfolio_from_ledgers(
        decisions_path,
        evaluations_path,
        starting_capital_eur=starting_capital_eur,
    ).to_dict()


def build_runtime_context(
    *,
    provider: MarketDataProvider,
    decisions_path: str | Path = "data/decisions.jsonl",
    evaluations_path: str | Path = "data/evaluations.jsonl",
    output_path: str | Path = "data/runtime_context.json",
    evidence_manifest_path: str | Path = "data/evidence_manifest.json",
    symbols: Sequence[str] | None = None,
    benchmark_symbol: str | None = None,
    candle_limit: int = 20,
    now_fn: Callable[[], datetime] = utc_now,
) -> dict[str, object]:
    if candle_limit < 2:
        raise ValueError("candle_limit must be >= 2")
    universe = tuple(symbols or PROTOCOL_V1.tradable_universe)
    benchmark = benchmark_symbol or PROTOCOL_V1.benchmark_symbol
    requested = tuple(dict.fromkeys((*universe, benchmark)))

    cutoff_dt = now_fn().astimezone(timezone.utc)
    cutoff_at = utc_iso(cutoff_dt)

    market: dict[str, object] = {}
    observed_times: list[str] = []
    for symbol in requested:
        quote = provider.get_quote(symbol)
        if not quote.market_open:
            raise MarketClosed(
                "US market is closed; forward cohort context is only built during an open trading session"
            )
        require_tradeable_quote(quote, now=cutoff_dt)
        candles = provider.get_candles(symbol, limit=candle_limit)
        market[symbol] = {
            "price": quote.price,
            "currency": quote.currency,
            "observed_at": quote.observed_at,
            "market_open": quote.market_open,
            "recent_candles": [
                {
                    "start_at": row.start_at,
                    "end_at": row.end_at,
                    "open": row.open,
                    "high": row.high,
                    "low": row.low,
                    "close": row.close,
                    "volume": row.volume,
                }
                for row in candles
            ],
        }
        observed_times.append(quote.observed_at)

    latest_observed = max(observed_times)
    evidence = build_evidence_context(
        [
            EvidenceRecord(
                url="https://data.alpaca.markets/v2/stocks/quotes/latest",
                source_name="Alpaca Market Data",
                kind=EvidenceKind.PRIMARY,
                title="US equity market snapshot",
                published_at=latest_observed,
                retrieved_at=cutoff_at,
                summary=(
                    f"Fresh normalized quote and recent candle snapshot for {len(universe)} "
                    "allowed US equities; exact values are supplied in the market context."
                ),
            ),
            EvidenceRecord(
                url=f"https://data.alpaca.markets/v2/stocks/{benchmark}/quotes/latest",
                source_name="Alpaca Market Data",
                kind=EvidenceKind.PRIMARY,
                title=f"{benchmark} benchmark snapshot",
                published_at=str(market[benchmark]["observed_at"]),
                retrieved_at=cutoff_at,
                summary=f"Fresh {benchmark} quote and recent candles for same-window benchmarking.",
            ),
        ],
        cutoff_at=cutoff_at,
    )
    manifest = write_evidence_manifest(evidence_manifest_path, evidence, cutoff_at=cutoff_at)

    payload = {
        "cutoff_at": cutoff_at,
        "portfolio": _portfolio_payload(
            Path(decisions_path), Path(evaluations_path), PROTOCOL_V1.starting_capital_eur
        ),
        "protocol": asdict(PROTOCOL_V1),
        "market": market,
        "evidence": [row.to_dict() for row in evidence],
        "evidence_manifest_sha256": manifest["records_sha256"],
    }
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    provider = AlpacaMarketDataProvider()
    payload = build_runtime_context(provider=provider)
    print(f"cutoff_at={payload['cutoff_at']} symbols={len(payload['market'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
