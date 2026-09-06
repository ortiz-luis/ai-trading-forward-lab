from io import BytesIO
from urllib.error import HTTPError

import pytest

from engine.providers.alpaca import (
    AlpacaAuthenticationError,
    AlpacaMarketDataProvider,
    AlpacaRateLimitError,
    ProviderHealthState,
)


class FakeTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, url, headers, timeout):
        self.calls.append((url, dict(headers), timeout))
        if url.endswith("/v2/clock"):
            return {"is_open": True}
        if "/quotes/latest" in url:
            return {"quote": {"bp": 99.0, "ap": 101.0, "t": "2026-09-06T14:00:00Z"}}
        if "/bars?" in url:
            return {
                "bars": [
                    {"t": "2026-09-06T13:59:00Z", "o": 98.0, "h": 101.0, "l": 97.0, "c": 100.0, "v": 1234},
                    {"t": "2026-09-06T13:58:00Z", "o": 97.0, "h": 99.0, "l": 96.0, "c": 98.0, "v": 999},
                ]
            }
        raise AssertionError(f"unexpected URL {url}")


def provider(transport):
    return AlpacaMarketDataProvider(
        api_key="test-key",
        api_secret="test-secret",
        transport=transport,
        sleep_fn=lambda _: None,
    )


def test_quote_normalization_and_no_secret_in_result():
    fake = FakeTransport()
    p = provider(fake)
    quote = p.get_quote("meta")
    assert quote.symbol == "META"
    assert quote.price == 100.0
    assert quote.currency == "USD"
    assert quote.market_open is True
    assert p.health.state == ProviderHealthState.HEALTHY
    serialized = repr(quote)
    assert "test-key" not in serialized
    assert "test-secret" not in serialized


def test_candles_normalized_and_sorted_oldest_first():
    p = provider(FakeTransport())
    candles = p.get_candles("AMD", limit=2)
    assert [c.start_at for c in candles] == [
        "2026-09-06T13:58:00Z",
        "2026-09-06T13:59:00Z",
    ]
    assert all(c.currency == "USD" for c in candles)


def test_missing_credentials_fail_closed(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY_ID", raising=False)
    monkeypatch.delenv("ALPACA_API_SECRET_KEY", raising=False)
    with pytest.raises(AlpacaAuthenticationError):
        AlpacaMarketDataProvider()


def test_authentication_error_not_retried():
    calls = {"n": 0}

    def transport(url, headers, timeout):
        calls["n"] += 1
        raise HTTPError(url, 401, "Unauthorized", {}, BytesIO())

    p = provider(transport)
    with pytest.raises(AlpacaAuthenticationError):
        p.get_quote("META")
    assert calls["n"] == 1
    assert p.health.state == ProviderHealthState.UNAVAILABLE


def test_rate_limit_has_bounded_retries():
    calls = {"n": 0}

    def transport(url, headers, timeout):
        calls["n"] += 1
        raise HTTPError(url, 429, "Too Many Requests", {}, BytesIO())

    p = AlpacaMarketDataProvider(
        api_key="test-key",
        api_secret="test-secret",
        transport=transport,
        max_retries=2,
        sleep_fn=lambda _: None,
    )
    with pytest.raises(AlpacaRateLimitError):
        p.get_quote("META")
    assert calls["n"] == 3
    assert p.health.state == ProviderHealthState.DEGRADED


def test_credentials_only_travel_in_headers():
    fake = FakeTransport()
    p = provider(fake)
    p.get_quote("META")
    for url, headers, _ in fake.calls:
        assert "test-key" not in url
        assert "test-secret" not in url
        assert headers["APCA-API-KEY-ID"] == "test-key"
        assert headers["APCA-API-SECRET-KEY"] == "test-secret"
