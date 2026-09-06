from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, Sequence
import json


@dataclass(frozen=True)
class MarketQuote:
    symbol: str
    price: float
    currency: str
    observed_at: str
    market_open: bool
    stale_after_seconds: int = 300

    def observed_datetime(self) -> datetime:
        parsed = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("observed_at must include timezone")
        return parsed.astimezone(timezone.utc)

    def is_stale(self, *, now: datetime) -> bool:
        if now.tzinfo is None:
            raise ValueError("now must include timezone")
        age = (now.astimezone(timezone.utc) - self.observed_datetime()).total_seconds()
        return age > self.stale_after_seconds

    def validate(self) -> None:
        if not self.symbol or self.symbol.upper() != self.symbol or not self.symbol.isascii():
            raise ValueError("symbol must be uppercase ASCII")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        if not self.currency or self.currency.upper() != self.currency:
            raise ValueError("currency must be uppercase")
        if self.stale_after_seconds <= 0:
            raise ValueError("stale_after_seconds must be > 0")
        self.observed_datetime()


@dataclass(frozen=True)
class MarketCandle:
    symbol: str
    start_at: str
    end_at: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    currency: str

    def validate(self) -> None:
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC prices must be > 0")
        if self.low > self.high:
            raise ValueError("low cannot exceed high")
        if self.volume < 0:
            raise ValueError("volume must be >= 0")
        for value in (self.start_at, self.end_at):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError("candle timestamps must include timezone")


class MarketDataProvider(Protocol):
    name: str

    def get_quote(self, symbol: str) -> MarketQuote:
        ...

    def get_candles(self, symbol: str, *, limit: int = 20) -> Sequence[MarketCandle]:
        ...


class MarketDataError(RuntimeError):
    pass


class MissingMarketData(MarketDataError):
    pass


class StaleMarketData(MarketDataError):
    pass


class MarketClosed(MarketDataError):
    pass


def require_tradeable_quote(quote: MarketQuote, *, now: datetime) -> MarketQuote:
    quote.validate()
    if not quote.market_open:
        raise MarketClosed(f"market closed for {quote.symbol}")
    if quote.is_stale(now=now):
        raise StaleMarketData(f"stale quote for {quote.symbol}")
    return quote


def write_audit_snapshot(path: str | Path, *, provider: str, quote: MarketQuote) -> None:
    quote.validate()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "provider": provider,
        "quote": asdict(quote),
    }
    target.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
