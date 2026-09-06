from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .schemas import DecisionEvent, EvaluationEvent


@dataclass(frozen=True)
class EvaluationRules:
    simulated_cost_bps: float = 5.0
    slippage_bps: float = 5.0

    def validate(self) -> None:
        if self.simulated_cost_bps < 0 or self.slippage_bps < 0:
            raise ValueError("cost/slippage bps must be >= 0")


@dataclass(frozen=True)
class PricePoint:
    observed_at: str
    price: float

    def validate(self) -> None:
        if self.price <= 0:
            raise ValueError("price must be > 0")


@dataclass(frozen=True)
class EvaluationResult:
    entry_price: float
    exit_price: float
    exit_reason: str
    gross_pnl_eur: float
    costs_eur: float
    net_pnl_eur: float
    benchmark_return_pct: float


def _effective_price(price: float, bps: float, *, side: str) -> float:
    factor = bps / 10000.0
    return price * (1 + factor if side == "buy" else 1 - factor)


def evaluate_long_decision(
    decision: DecisionEvent,
    *,
    asset_prices: Sequence[PricePoint],
    benchmark_prices: Sequence[PricePoint],
    rules: EvaluationRules | None = None,
    explicit_sell_index: int | None = None,
) -> EvaluationResult:
    """Evaluate a locked BUY using only forward price points.

    Price point 0 is the first eligible post-cutoff entry observation. The exit is
    the first stop hit, an explicit later SELL index if supplied, or otherwise the
    final point supplied for the frozen horizon. Benchmark uses the identical
    entry/exit indices.
    """
    active = rules or EvaluationRules()
    active.validate()
    decision.validate()
    if decision.action.value != "BUY":
        raise ValueError("deterministic evaluator evaluates locked BUY decisions")
    if len(asset_prices) < 2 or len(benchmark_prices) < len(asset_prices):
        raise ValueError("aligned entry/exit asset and benchmark prices are required")
    if explicit_sell_index is not None and not (1 <= explicit_sell_index < len(asset_prices)):
        raise ValueError("explicit_sell_index must reference a post-entry price point")

    for point in (*asset_prices, *benchmark_prices):
        point.validate()

    entry = _effective_price(asset_prices[0].price, active.slippage_bps, side="buy")
    stop_price = entry * (1 + (decision.stop_pct or 0.0))

    planned_exit_index = explicit_sell_index if explicit_sell_index is not None else len(asset_prices) - 1
    exit_index = planned_exit_index
    exit_reason = "explicit_sell" if explicit_sell_index is not None else "horizon"

    for index, point in enumerate(asset_prices[1:planned_exit_index + 1], start=1):
        if decision.stop_pct is not None and point.price <= stop_price:
            exit_index = index
            exit_reason = "stop"
            break

    exit_price = _effective_price(asset_prices[exit_index].price, active.slippage_bps, side="sell")
    quantity = decision.notional_eur / entry
    gross_pnl = quantity * (exit_price - entry)
    costs = decision.notional_eur * (active.simulated_cost_bps / 10000.0) * 2
    net_pnl = gross_pnl - costs

    b0 = benchmark_prices[0].price
    b1 = benchmark_prices[exit_index].price
    benchmark_return_pct = ((b1 / b0) - 1) * 100.0

    return EvaluationResult(
        entry_price=entry,
        exit_price=exit_price,
        exit_reason=exit_reason,
        gross_pnl_eur=gross_pnl,
        costs_eur=costs,
        net_pnl_eur=net_pnl,
        benchmark_return_pct=benchmark_return_pct,
    )


def to_evaluation_event(
    result: EvaluationResult,
    *,
    evaluation_id: str,
    decision_id: str,
    evaluated_at: str,
) -> EvaluationEvent:
    return EvaluationEvent(
        evaluation_id=evaluation_id,
        decision_id=decision_id,
        evaluated_at=evaluated_at,
        exit_reason=result.exit_reason,
        exit_price=result.exit_price,
        gross_pnl_eur=result.gross_pnl_eur,
        costs_eur=result.costs_eur,
        net_pnl_eur=result.net_pnl_eur,
        benchmark_return_pct=result.benchmark_return_pct,
    )
