from datetime import datetime, timezone

import pytest

from engine.providers.fixture import FixtureMarketDataProvider
from engine.providers.market import (
    MarketCandle,
    MarketClosed,
    MarketQuote,
    MissingMarketData,
    StaleMarketData,
    require_tradeable_quote,
)


def quote(*, observed_at: str = "2026-09-06T14:00:00Z", market_open: bool = True) -> MarketQuote:
    return MarketQuote(
        symbol="META",
        price=100.0,
        currency="USD",
        observed_at=observed_at,
        market_open=market_open,
        stale_after_seconds=300,
    )


def test_fixture_provider_is_deterministic():
    q = quote()
    provider = FixtureMarketDataProvider(quotes={"META": q})
    assert provider.get_quote("META") == q
    assert provider.get_quote("META") == q


def test_missing_quote_fails_explicitly():
    provider = FixtureMarketDataProvider()
    with pytest.raises(MissingMarketData):
        provider.get_quote("META")


def test_stale_quote_cannot_be_tradeable():
    q = quote(observed_at="2026-09-06T14:00:00Z")
    now = datetime(2026, 9, 6, 14, 6, tzinfo=timezone.utc)
    with pytest.raises(StaleMarketData):
        require_tradeable_quote(q, now=now)


def test_closed_market_quote_cannot_be_tradeable():
    q = quote(market_open=False)
    now = datetime(2026, 9, 6, 14, 1, tzinfo=timezone.utc)
    with pytest.raises(MarketClosed):
        require_tradeable_quote(q, now=now)


def test_fresh_open_quote_is_tradeable():
    q = quote(observed_at="2026-09-06T14:00:00Z")
    now = datetime(2026, 9, 6, 14, 4, tzinfo=timezone.utc)
    assert require_tradeable_quote(q, now=now) == q


def test_candle_model_validates_ohlc_and_time():
    candle = MarketCandle(
        symbol="META",
        start_at="2026-09-06T13:59:00Z",
        end_at="2026-09-06T14:00:00Z",
        open=99.0,
        high=101.0,
        low=98.5,
        close=100.0,
        volume=12345,
        currency="USD",
    )
    candle.validate()

    bad = MarketCandle(
        symbol="META",
        start_at="2026-09-06T13:59:00Z",
        end_at="2026-09-06T14:00:00Z",
        open=99.0,
        high=98.0,
        low=101.0,
        close=100.0,
        volume=12345,
        currency="USD",
    )
    with pytest.raises(ValueError):
        bad.validate()
