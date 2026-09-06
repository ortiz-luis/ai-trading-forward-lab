from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .schemas import EvaluationEvent


@dataclass(frozen=True)
class ConfidenceObservation:
    confidence: float
    outcome_positive: bool


@dataclass(frozen=True)
class ExperimentStatistics:
    starting_capital_eur: float
    current_equity_eur: float
    total_net_pnl_eur: float
    wins: int
    losses: int
    breakeven: int
    no_trades: int
    errors: int
    benchmark_return_pct_mean: float
    max_drawdown_pct: float
    confidence_brier_score: float | None
    score_points: int


def _max_drawdown_pct(equity_curve: Sequence[float]) -> float:
    if not equity_curve:
        return 0.0
    peak = equity_curve[0]
    worst = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            drawdown = (value / peak - 1.0) * 100.0
            worst = min(worst, drawdown)
    return worst


def _brier_score(observations: Sequence[ConfidenceObservation]) -> float | None:
    if not observations:
        return None
    values = []
    for item in observations:
        if not 0 <= item.confidence <= 1:
            raise ValueError("confidence must be in [0,1]")
        target = 1.0 if item.outcome_positive else 0.0
        values.append((item.confidence - target) ** 2)
    return sum(values) / len(values)


def build_statistics(
    evaluations: Iterable[EvaluationEvent],
    *,
    starting_capital_eur: float = 1000.0,
    no_trades: int = 0,
    errors: int = 0,
    confidence_observations: Sequence[ConfidenceObservation] = (),
) -> ExperimentStatistics:
    rows = list(evaluations)
    net = [row.net_pnl_eur for row in rows]
    wins = sum(value > 0 for value in net)
    losses = sum(value < 0 for value in net)
    breakeven = sum(value == 0 for value in net)

    equity = starting_capital_eur
    curve = [equity]
    for value in net:
        equity += value
        curve.append(equity)

    benchmark_mean = (
        sum(row.benchmark_return_pct for row in rows) / len(rows)
        if rows else 0.0
    )

    # Secondary game score only. Monetary P&L remains the primary performance truth.
    points = 0
    for row in rows:
        if row.net_pnl_eur > 0:
            points += 2
        trade_return_pct = (row.net_pnl_eur / starting_capital_eur) * 100.0
        if trade_return_pct > row.benchmark_return_pct:
            points += 1

    return ExperimentStatistics(
        starting_capital_eur=starting_capital_eur,
        current_equity_eur=equity,
        total_net_pnl_eur=sum(net),
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        no_trades=no_trades,
        errors=errors,
        benchmark_return_pct_mean=benchmark_mean,
        max_drawdown_pct=_max_drawdown_pct(curve),
        confidence_brier_score=_brier_score(confidence_observations),
        score_points=points,
    )
