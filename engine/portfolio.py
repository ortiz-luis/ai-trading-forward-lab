from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .ledger import read_jsonl
from .schemas import Action, DecisionEvent


@dataclass(frozen=True)
class Position:
    symbol: str
    notional_eur: float


@dataclass(frozen=True)
class PortfolioRules:
    max_position_pct: float = 0.15
    max_total_exposure_pct: float = 0.45
    max_open_positions: int = 3

    def validate(self) -> None:
        if not 0 < self.max_position_pct <= 1:
            raise ValueError("max_position_pct must be in (0, 1]")
        if not 0 < self.max_total_exposure_pct <= 1:
            raise ValueError("max_total_exposure_pct must be in (0, 1]")
        if self.max_position_pct > self.max_total_exposure_pct:
            raise ValueError("max_position_pct cannot exceed max_total_exposure_pct")
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be >= 1")


@dataclass
class PortfolioState:
    starting_capital_eur: float
    cash_eur: float
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl_eur: float = 0.0

    @property
    def exposure_eur(self) -> float:
        return sum(p.notional_eur for p in self.positions.values())

    @property
    def equity_eur(self) -> float:
        # Until mark-to-market prices arrive in a later gate, equity is carried at cost.
        return self.cash_eur + self.exposure_eur

    @classmethod
    def initial(cls, starting_capital_eur: float) -> "PortfolioState":
        if starting_capital_eur <= 0:
            raise ValueError("starting_capital_eur must be > 0")
        return cls(starting_capital_eur=starting_capital_eur, cash_eur=starting_capital_eur)

    def validate(self, rules: PortfolioRules) -> None:
        rules.validate()
        if self.cash_eur < -1e-9:
            raise ValueError("cash cannot be negative")
        if len(self.positions) > rules.max_open_positions:
            raise ValueError("too many open positions")
        max_position = self.equity_eur * rules.max_position_pct
        for position in self.positions.values():
            if position.notional_eur < 0:
                raise ValueError("position notional cannot be negative")
            if position.notional_eur > max_position + 1e-9:
                raise ValueError("position exceeds max_position_pct")
        if self.exposure_eur > self.equity_eur * rules.max_total_exposure_pct + 1e-9:
            raise ValueError("total exposure exceeds max_total_exposure_pct")

    def to_dict(self) -> dict[str, object]:
        return {
            "starting_capital_eur": self.starting_capital_eur,
            "cash_eur": self.cash_eur,
            "equity_eur": self.equity_eur,
            "exposure_eur": self.exposure_eur,
            "realized_pnl_eur": self.realized_pnl_eur,
            "positions": {
                symbol: asdict(position)
                for symbol, position in sorted(self.positions.items())
            },
        }


def apply_decision(state: PortfolioState, event: DecisionEvent, rules: PortfolioRules) -> PortfolioState:
    """Apply an accounting-only decision transition.

    BUY opens one new long position at notional cost. HOLD and NO_TRADE leave
    accounting unchanged. SELL closes the full cost-basis position; realized P&L
    remains zero until actual exit prices are introduced by the evaluator gate.
    """
    event.validate()
    rules.validate()

    next_state = PortfolioState(
        starting_capital_eur=state.starting_capital_eur,
        cash_eur=state.cash_eur,
        positions=dict(state.positions),
        realized_pnl_eur=state.realized_pnl_eur,
    )

    if event.action == Action.NO_TRADE:
        pass
    elif event.action == Action.HOLD:
        if event.symbol not in next_state.positions:
            raise ValueError("cannot HOLD a symbol without an open position")
        if event.notional_eur != 0:
            raise ValueError("HOLD must use notional_eur=0")
    elif event.action == Action.BUY:
        assert event.symbol is not None
        if event.symbol in next_state.positions:
            raise ValueError("BUY cannot add to an existing position in v1")
        if event.notional_eur <= 0:
            raise ValueError("BUY requires positive notional_eur")
        if event.notional_eur > next_state.cash_eur + 1e-9:
            raise ValueError("insufficient cash")
        next_state.cash_eur -= event.notional_eur
        next_state.positions[event.symbol] = Position(event.symbol, event.notional_eur)
    elif event.action == Action.SELL:
        assert event.symbol is not None
        if event.symbol not in next_state.positions:
            raise ValueError("cannot SELL a symbol without an open position")
        if event.notional_eur != 0:
            raise ValueError("SELL must use notional_eur=0 until evaluator supplies exit proceeds")
        position = next_state.positions.pop(event.symbol)
        next_state.cash_eur += position.notional_eur
    else:
        raise ValueError(f"unsupported action: {event.action}")

    next_state.validate(rules)
    return next_state


def rebuild_portfolio(
    decisions: Iterable[DecisionEvent],
    *,
    starting_capital_eur: float = 1000.0,
    rules: PortfolioRules | None = None,
) -> PortfolioState:
    active_rules = rules or PortfolioRules()
    state = PortfolioState.initial(starting_capital_eur)
    state.validate(active_rules)
    for event in decisions:
        state = apply_decision(state, event, active_rules)
    return state


def rebuild_portfolio_from_ledger(
    path: str | Path,
    *,
    starting_capital_eur: float = 1000.0,
    rules: PortfolioRules | None = None,
) -> PortfolioState:
    decisions = [DecisionEvent.from_dict(row) for row in read_jsonl(path)]
    return rebuild_portfolio(
        decisions,
        starting_capital_eur=starting_capital_eur,
        rules=rules,
    )
