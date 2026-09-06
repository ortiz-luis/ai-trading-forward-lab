from datetime import datetime, timezone

import pytest

from engine.providers.fixture import FixtureMarketDataProvider
from engine.providers.market import MarketCandle, MarketQuote, StaleMarketData
from engine.runtime_context import build_runtime_context


def candle(symbol, minute, close):
    return MarketCandle(
        symbol=symbol,
        start_at=f"2026-09-06T13:{minute:02d}:00Z",
        end_at=f"2026-09-06T13:{minute+1:02d}:00Z",
        open=close - 0.2,
        high=close + 0.3,
        low=close - 0.4,
        close=close,
        volume=1000,
        currency="USD",
    )


def provider(observed_at="2026-09-06T13:59:00Z"):
    quotes = {
        "META": MarketQuote("META", 100.0, "USD", observed_at, True, 300),
        "SPY": MarketQuote("SPY", 500.0, "USD", observed_at, True, 300),
    }
    candles = {
        "META": [candle("META", 57, 99.5), candle("META", 58, 100.0)],
        "SPY": [candle("SPY", 57, 499.0), candle("SPY", 58, 500.0)],
    }
    return FixtureMarketDataProvider(quotes=quotes, candles=candles)


def fixed_now():
    return datetime(2026, 9, 6, 14, 0, 0, tzinfo=timezone.utc)


def test_runtime_context_is_fresh_deterministic_and_audited(tmp_path):
    output = tmp_path / "runtime_context.json"
    manifest = tmp_path / "evidence_manifest.json"
    payload = build_runtime_context(
        provider=provider(),
        decisions_path=tmp_path / "decisions.jsonl",
        output_path=output,
        evidence_manifest_path=manifest,
        symbols=("META",),
        benchmark_symbol="SPY",
        candle_limit=2,
        now_fn=fixed_now,
    )
    assert payload["cutoff_at"] == "2026-09-06T14:00:00Z"
    assert set(payload["market"]) == {"META", "SPY"}
    assert payload["portfolio"]["equity_eur"] == 1000.0
    assert len(payload["evidence"]) == 2
    assert len(payload["evidence_manifest_sha256"]) == 64
    assert output.exists() and manifest.exists()


def test_stale_quote_fails_closed_before_context_write(tmp_path):
    with pytest.raises(StaleMarketData):
        build_runtime_context(
            provider=provider("2026-09-06T13:50:00Z"),
            decisions_path=tmp_path / "decisions.jsonl",
            output_path=tmp_path / "runtime_context.json",
            evidence_manifest_path=tmp_path / "evidence_manifest.json",
            symbols=("META",),
            benchmark_symbol="SPY",
            candle_limit=2,
            now_fn=fixed_now,
        )
    assert not (tmp_path / "runtime_context.json").exists()
