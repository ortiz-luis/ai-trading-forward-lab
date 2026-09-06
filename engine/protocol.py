from __future__ import annotations

from dataclasses import dataclass

from .schemas import Action, DecisionEvent


@dataclass(frozen=True)
class TradingProtocol:
    version: str
    tradable_universe: tuple[str, ...]
    benchmark_symbol: str
    starting_capital_eur: float
    max_open_positions: int
    max_position_pct: float
    max_total_exposure_pct: float
    min_buy_notional_eur: float
    min_horizon_days: int
    max_horizon_days: int
    default_horizon_days: int
    min_stop_pct: float
    max_stop_pct: float
    default_stop_pct: float
    long_only: bool = True
    allow_pyramiding: bool = False
    max_scheduled_cycles_per_us_trading_day: int = 1

    def validate(self) -> None:
        if not self.version:
            raise ValueError("version is required")
        if not self.tradable_universe:
            raise ValueError("tradable_universe cannot be empty")
        if self.benchmark_symbol in self.tradable_universe:
            raise ValueError("benchmark must not be tradable in v1")
        if self.starting_capital_eur <= 0:
            raise ValueError("starting capital must be > 0")
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be >= 1")
        if not 0 < self.max_position_pct <= self.max_total_exposure_pct <= 1:
            raise ValueError("invalid exposure percentages")
        if self.min_buy_notional_eur <= 0:
            raise ValueError("min_buy_notional_eur must be > 0")
        if not (1 <= self.min_horizon_days <= self.default_horizon_days <= self.max_horizon_days):
            raise ValueError("invalid horizon bounds")
        if not (-1.0 < self.max_stop_pct < self.min_stop_pct < 0):
            raise ValueError("stop bounds must be negative percentages")
        if not (self.max_stop_pct <= self.default_stop_pct <= self.min_stop_pct):
            raise ValueError("default stop must lie within stop bounds")
        if self.max_scheduled_cycles_per_us_trading_day != 1:
            raise ValueError("v1 permits exactly one scheduled cycle per US trading day")

    def validate_decision(self, event: DecisionEvent, *, current_equity_eur: float) -> None:
        self.validate()
        event.validate()
        if current_equity_eur <= 0:
            raise ValueError("current_equity_eur must be > 0")

        if event.action == Action.BUY:
            if event.symbol not in self.tradable_universe:
                raise ValueError("symbol is outside tradable universe")
            max_notional = current_equity_eur * self.max_position_pct
            effective_min = min(self.min_buy_notional_eur, max_notional)
            if event.notional_eur < effective_min:
                raise ValueError("BUY notional is below protocol minimum")
            if event.notional_eur > max_notional + 1e-9:
                raise ValueError("BUY notional exceeds max_position_pct")
            if not self.min_horizon_days <= event.horizon_days <= self.max_horizon_days:
                raise ValueError("BUY horizon outside protocol bounds")
            if event.stop_pct is None:
                raise ValueError("BUY requires stop_pct")
            if not self.max_stop_pct <= event.stop_pct <= self.min_stop_pct:
                raise ValueError("BUY stop outside protocol bounds")

        elif event.action == Action.HOLD:
            if event.symbol not in self.tradable_universe:
                raise ValueError("HOLD symbol is outside tradable universe")
            if event.notional_eur != 0:
                raise ValueError("HOLD must allocate zero notional")

        elif event.action == Action.SELL:
            if event.symbol not in self.tradable_universe:
                raise ValueError("SELL symbol is outside tradable universe")
            if event.notional_eur != 0:
                raise ValueError("SELL must allocate zero notional")

        elif event.action == Action.NO_TRADE:
            if event.symbol is not None or event.notional_eur != 0:
                raise ValueError("NO_TRADE cannot allocate a symbol or notional")


PROTOCOL_V1 = TradingProtocol(
    version="v1",
    tradable_universe=(
        "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "AVGO", "AMD",
        "NFLX", "JPM", "V", "MA", "COST", "WMT", "UNH", "LLY", "XOM", "CVX",
    ),
    benchmark_symbol="SPY",
    starting_capital_eur=1000.0,
    max_open_positions=3,
    max_position_pct=0.15,
    max_total_exposure_pct=0.45,
    min_buy_notional_eur=50.0,
    min_horizon_days=2,
    max_horizon_days=10,
    default_horizon_days=5,
    min_stop_pct=-0.01,
    max_stop_pct=-0.05,
    default_stop_pct=-0.02,
)
