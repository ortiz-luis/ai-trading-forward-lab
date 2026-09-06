from __future__ import annotations

from typing import Sequence

from .market import MarketCandle, MarketDataProvider, MarketQuote, MissingMarketData


class FixtureMarketDataProvider(MarketDataProvider):
    name = "fixture"

    def __init__(
        self,
        *,
        quotes: dict[str, MarketQuote] | None = None,
        candles: dict[str, Sequence[MarketCandle]] | None = None,
    ) -> None:
        self._quotes = dict(quotes or {})
        self._candles = {symbol: list(rows) for symbol, rows in (candles or {}).items()}

    def get_quote(self, symbol: str) -> MarketQuote:
        try:
            return self._quotes[symbol]
        except KeyError as exc:
            raise MissingMarketData(f"missing quote for {symbol}") from exc

    def get_candles(self, symbol: str, *, limit: int = 20) -> Sequence[MarketCandle]:
        if limit <= 0:
            raise ValueError("limit must be > 0")
        try:
            rows = self._candles[symbol]
        except KeyError as exc:
            raise MissingMarketData(f"missing candles for {symbol}") from exc
        return tuple(rows[-limit:])
