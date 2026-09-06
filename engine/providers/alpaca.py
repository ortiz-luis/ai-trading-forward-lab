from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
import json
import os
import time
from typing import Any, Callable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .market import MarketCandle, MarketDataError, MarketQuote, MissingMarketData


class AlpacaProviderError(MarketDataError):
    pass


class AlpacaAuthenticationError(AlpacaProviderError):
    pass


class AlpacaRateLimitError(AlpacaProviderError):
    pass


class ProviderHealthState(StrEnum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class ProviderHealth:
    state: ProviderHealthState
    checked_at: str
    message: str


Transport = Callable[[str, dict[str, str], float], dict[str, Any]]


def _default_transport(url: str, headers: dict[str, str], timeout: float) -> dict[str, Any]:
    request = Request(url=url, headers=headers, method="GET")
    with urlopen(request, timeout=timeout) as response:  # nosec B310: fixed HTTPS Alpaca bases only
        return json.loads(response.read().decode("utf-8"))


class AlpacaMarketDataProvider:
    """Alpaca-backed implementation of the v1 MarketDataProvider contract.

    Credentials are read from the environment at construction time and are used
    only as request headers. They are never exposed in returned observations.
    """

    name = "alpaca"
    data_base_url = "https://data.alpaca.markets"
    paper_base_url = "https://paper-api.alpaca.markets"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        feed: str = "iex",
        currency: str = "USD",
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 0.5,
        transport: Transport | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key or os.environ.get("ALPACA_API_KEY_ID", "")
        self._api_secret = api_secret or os.environ.get("ALPACA_API_SECRET_KEY", "")
        if not self._api_key or not self._api_secret:
            raise AlpacaAuthenticationError(
                "missing Alpaca credentials; set ALPACA_API_KEY_ID and ALPACA_API_SECRET_KEY"
            )
        if feed not in {"iex", "sip", "delayed_sip", "boats", "overnight", "otc"}:
            raise ValueError("unsupported Alpaca feed")
        if not currency.isalpha() or len(currency) != 3:
            raise ValueError("currency must be a 3-letter ISO code")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        self.feed = feed
        self.currency = currency.upper()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self._transport = transport or _default_transport
        self._sleep = sleep_fn
        self._last_health = ProviderHealth(
            ProviderHealthState.DEGRADED,
            datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "not checked yet",
        )

    @property
    def health(self) -> ProviderHealth:
        return self._last_health

    def _headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": self._api_key,
            "APCA-API-SECRET-KEY": self._api_secret,
            "Accept": "application/json",
        }

    def _request_json(self, url: str) -> dict[str, Any]:
        attempt = 0
        while True:
            try:
                payload = self._transport(url, self._headers(), self.timeout_seconds)
                self._set_health(ProviderHealthState.HEALTHY, "request succeeded")
                return payload
            except HTTPError as exc:
                if exc.code in {401, 403}:
                    self._set_health(ProviderHealthState.UNAVAILABLE, "authentication/permission failure")
                    raise AlpacaAuthenticationError("Alpaca authentication or permission failure") from exc
                if exc.code == 429:
                    if attempt >= self.max_retries:
                        self._set_health(ProviderHealthState.DEGRADED, "rate limited")
                        raise AlpacaRateLimitError("Alpaca rate limit exceeded") from exc
                elif 500 <= exc.code < 600:
                    if attempt >= self.max_retries:
                        self._set_health(ProviderHealthState.UNAVAILABLE, f"server error {exc.code}")
                        raise AlpacaProviderError(f"Alpaca server error {exc.code}") from exc
                else:
                    self._set_health(ProviderHealthState.UNAVAILABLE, f"HTTP error {exc.code}")
                    raise AlpacaProviderError(f"Alpaca HTTP error {exc.code}") from exc
            except (URLError, TimeoutError, OSError) as exc:
                if attempt >= self.max_retries:
                    self._set_health(ProviderHealthState.UNAVAILABLE, "network failure")
                    raise AlpacaProviderError("Alpaca network failure") from exc
            attempt += 1
            self._sleep(self.retry_backoff_seconds * (2 ** (attempt - 1)))

    def _set_health(self, state: ProviderHealthState, message: str) -> None:
        self._last_health = ProviderHealth(
            state=state,
            checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            message=message,
        )

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        normalized = symbol.strip().upper()
        if not normalized or not normalized.isascii():
            raise ValueError("symbol must be non-empty ASCII")
        return normalized

    def _market_open(self) -> bool:
        payload = self._request_json(f"{self.paper_base_url}/v2/clock")
        value = payload.get("is_open")
        if not isinstance(value, bool):
            raise AlpacaProviderError("clock response missing boolean is_open")
        return value

    def get_quote(self, symbol: str) -> MarketQuote:
        symbol = self._normalize_symbol(symbol)
        params = urlencode({"feed": self.feed, "currency": self.currency})
        payload = self._request_json(
            f"{self.data_base_url}/v2/stocks/{symbol}/quotes/latest?{params}"
        )
        quote = payload.get("quote")
        if not isinstance(quote, dict):
            raise MissingMarketData(f"missing quote for {symbol}")
        bid = quote.get("bp")
        ask = quote.get("ap")
        timestamp = quote.get("t")
        if not isinstance(bid, (int, float)) or not isinstance(ask, (int, float)):
            raise MissingMarketData(f"quote for {symbol} is missing bid/ask")
        if bid <= 0 and ask <= 0:
            raise MissingMarketData(f"quote for {symbol} has no positive bid/ask")
        if bid > 0 and ask > 0:
            price = (float(bid) + float(ask)) / 2.0
        else:
            price = float(ask if ask > 0 else bid)
        if not isinstance(timestamp, str):
            raise MissingMarketData(f"quote for {symbol} is missing timestamp")
        result = MarketQuote(
            symbol=symbol,
            price=price,
            currency=self.currency,
            observed_at=timestamp,
            market_open=self._market_open(),
            stale_after_seconds=300,
        )
        result.validate()
        return result

    def get_candles(self, symbol: str, *, limit: int = 20) -> Sequence[MarketCandle]:
        symbol = self._normalize_symbol(symbol)
        if not 1 <= limit <= 10000:
            raise ValueError("limit must be in [1, 10000]")

        # Alpaca may return an empty latest-bars response outside a live session
        # when no explicit historical window is supplied. Use a bounded UTC
        # lookback that safely spans weekends and US market holidays.
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=14)
        params = urlencode(
            {
                "timeframe": "1Min",
                "start": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "end": end.isoformat(timespec="seconds").replace("+00:00", "Z"),
                "limit": str(limit),
                "adjustment": "raw",
                "feed": self.feed,
                "currency": self.currency,
                "sort": "desc",
            }
        )
        payload = self._request_json(f"{self.data_base_url}/v2/stocks/{symbol}/bars?{params}")
        bars = payload.get("bars")
        if not isinstance(bars, list) or not bars:
            raise MissingMarketData(f"missing bars for {symbol} in 14-day historical window")
        result: list[MarketCandle] = []
        for bar in bars:
            if not isinstance(bar, dict) or not isinstance(bar.get("t"), str):
                raise MissingMarketData(f"malformed bar for {symbol}")
            start_at = datetime.fromisoformat(bar["t"].replace("Z", "+00:00")).astimezone(timezone.utc)
            end_at = start_at + timedelta(minutes=1)
            candle = MarketCandle(
                symbol=symbol,
                start_at=start_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
                end_at=end_at.isoformat(timespec="seconds").replace("+00:00", "Z"),
                open=float(bar["o"]),
                high=float(bar["h"]),
                low=float(bar["l"]),
                close=float(bar["c"]),
                volume=float(bar["v"]),
                currency=self.currency,
            )
            candle.validate()
            result.append(candle)
        result.sort(key=lambda row: row.start_at)
        return tuple(result)
