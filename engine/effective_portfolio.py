from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .ledger import read_jsonl
from .protocol import PROTOCOL_V1, TradingProtocol
from .schemas import Action, DecisionEvent, EvaluationEvent


@dataclass(frozen=True)
class EffectivePosition:
    symbol: str
    decision_id: str
    notional_eur: float


@dataclass(frozen=True)
class EffectivePortfolio:
    starting_capital_eur: float
    cash_eur: float
    positions: dict[str, EffectivePosition]
    realized_pnl_eur: float

    @property
    def exposure_eur(self) -> float:
        return sum(row.notional_eur for row in self.positions.values())

    @property
    def equity_eur(self) -> float:
        return self.cash_eur + self.exposure_eur

    def to_dict(self) -> dict[str, object]:
        return {
            "starting_capital_eur": self.starting_capital_eur,
            "cash_eur": self.cash_eur,
            "equity_eur": self.equity_eur,
            "exposure_eur": self.exposure_eur,
            "realized_pnl_eur": self.realized_pnl_eur,
            "unrealized_pnl_eur": 0.0,
            "positions": {
                symbol: {
                    "symbol": row.symbol,
                    "decision_id": row.decision_id,
                    "notional_eur": row.notional_eur,
                }
                for symbol, row in sorted(self.positions.items())
            },
        }


def validate_decision_against_effective_portfolio(
    event: DecisionEvent,
    portfolio: EffectivePortfolio,
    *,
    protocol: TradingProtocol = PROTOCOL_V1,
) -> None:
    protocol.validate_decision(event, current_equity_eur=portfolio.equity_eur)
    if event.action == Action.BUY:
        assert event.symbol is not None
        if event.symbol in portfolio.positions:
            raise ValueError("pyramiding/existing symbol is forbidden")
        if len(portfolio.positions) >= protocol.max_open_positions:
            raise ValueError("max_open_positions reached")
        if event.notional_eur > portfolio.cash_eur + 1e-9:
            raise ValueError("insufficient effective cash")
        if portfolio.exposure_eur + event.notional_eur > portfolio.equity_eur * protocol.max_total_exposure_pct + 1e-9:
            raise ValueError("BUY would exceed total exposure limit")
    elif event.action in {Action.HOLD, Action.SELL}:
        assert event.symbol is not None
        if event.symbol not in portfolio.positions:
            raise ValueError(f"{event.action.value} requires an effective open position")


def _ts(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("event timestamp must include timezone")
    return parsed


def rebuild_effective_portfolio(
    decisions: Iterable[DecisionEvent],
    evaluations: Iterable[EvaluationEvent],
    *,
    starting_capital_eur: float = 1000.0,
) -> EffectivePortfolio:
    if starting_capital_eur <= 0:
        raise ValueError("starting_capital_eur must be > 0")

    decisions = list(decisions)
    evaluations = list(evaluations)
    decision_by_id = {row.decision_id: row for row in decisions}
    timeline: list[tuple[datetime, int, object]] = []
    for row in decisions:
        row.validate()
        timeline.append((_ts(row.decision_at), 0, row))
    for row in evaluations:
        row.validate()
        if row.decision_id not in decision_by_id:
            raise ValueError(f"evaluation references unknown decision {row.decision_id}")
        timeline.append((_ts(row.evaluated_at), 1, row))
    timeline.sort(key=lambda item: (item[0], item[1]))

    cash = starting_capital_eur
    realized = 0.0
    positions: dict[str, EffectivePosition] = {}
    sold_pending_evaluation: set[str] = set()

    for _, _, event in timeline:
        if isinstance(event, DecisionEvent):
            if event.action == Action.BUY:
                assert event.symbol is not None
                if event.symbol in positions:
                    raise ValueError(f"duplicate open symbol {event.symbol}")
                if event.notional_eur > cash + 1e-9:
                    raise ValueError("insufficient effective cash")
                cash -= event.notional_eur
                positions[event.symbol] = EffectivePosition(
                    symbol=event.symbol,
                    decision_id=event.decision_id,
                    notional_eur=event.notional_eur,
                )
            elif event.action == Action.SELL:
                assert event.symbol is not None
                position = positions.pop(event.symbol, None)
                if position is not None:
                    cash += position.notional_eur
                    sold_pending_evaluation.add(position.decision_id)
            elif event.action in {Action.HOLD, Action.NO_TRADE}:
                pass
        else:
            assert isinstance(event, EvaluationEvent)
            original = decision_by_id[event.decision_id]
            if original.action != Action.BUY or not original.symbol:
                continue
            position = positions.get(original.symbol)
            if position is not None and position.decision_id == original.decision_id:
                positions.pop(original.symbol)
                cash += position.notional_eur + event.net_pnl_eur
                realized += event.net_pnl_eur
            elif original.decision_id in sold_pending_evaluation:
                cash += event.net_pnl_eur
                realized += event.net_pnl_eur
                sold_pending_evaluation.remove(original.decision_id)

    return EffectivePortfolio(
        starting_capital_eur=starting_capital_eur,
        cash_eur=cash,
        positions=positions,
        realized_pnl_eur=realized,
    )


def rebuild_effective_portfolio_from_ledgers(
    decisions_path: str | Path,
    evaluations_path: str | Path,
    *,
    starting_capital_eur: float = 1000.0,
) -> EffectivePortfolio:
    decisions = [DecisionEvent.from_dict(row) for row in read_jsonl(decisions_path)]
    evaluations = [EvaluationEvent.from_dict(row) for row in read_jsonl(evaluations_path)]
    return rebuild_effective_portfolio(
        decisions,
        evaluations,
        starting_capital_eur=starting_capital_eur,
    )
