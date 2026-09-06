import pytest

from engine.effective_portfolio import (
    rebuild_effective_portfolio,
    validate_decision_against_effective_portfolio,
)
from engine.schemas import Action, DecisionEvent, EvaluationEvent


def decision(decision_id, at, action, symbol, notional=0.0):
    return DecisionEvent(
        decision_id=decision_id,
        idempotency_key=f"k-{decision_id}",
        decision_at=at,
        cutoff_at=at,
        action=action,
        symbol=symbol,
        notional_eur=notional,
        confidence=0.7,
        horizon_days=5 if action == Action.BUY else 0,
        stop_pct=-0.02 if action == Action.BUY else None,
        thesis="fixture",
        counter_thesis="fixture",
        prompt_version="trading-v1",
        model="fixture",
        sources_hash="fixture",
    )


def evaluation(decision_id, at, pnl):
    return EvaluationEvent(
        evaluation_id=f"e-{decision_id}",
        decision_id=decision_id,
        evaluated_at=at,
        exit_reason="horizon",
        exit_price=105.0,
        gross_pnl_eur=pnl + 0.1,
        costs_eur=0.1,
        net_pnl_eur=pnl,
        benchmark_return_pct=1.0,
    )


def test_auto_evaluation_closes_position_and_restores_cash_with_pnl():
    buy = decision("b1", "2026-09-07T14:00:00Z", Action.BUY, "META", 100.0)
    state = rebuild_effective_portfolio([buy], [evaluation("b1", "2026-09-09T14:00:00Z", 5.0)])
    assert state.positions == {}
    assert state.cash_eur == 1005.0
    assert state.equity_eur == 1005.0
    assert state.realized_pnl_eur == 5.0


def test_sell_then_evaluation_adds_only_realized_pnl_once():
    buy = decision("b1", "2026-09-07T14:00:00Z", Action.BUY, "META", 100.0)
    sell = decision("s1", "2026-09-08T14:00:00Z", Action.SELL, "META", 0.0)
    state = rebuild_effective_portfolio(
        [buy, sell],
        [evaluation("b1", "2026-09-08T14:05:00Z", 3.0)],
    )
    assert state.positions == {}
    assert state.cash_eur == 1003.0
    assert state.realized_pnl_eur == 3.0


def test_later_rebuy_is_not_closed_by_old_evaluation():
    buy1 = decision("b1", "2026-09-07T14:00:00Z", Action.BUY, "META", 100.0)
    eval1 = evaluation("b1", "2026-09-08T14:00:00Z", 2.0)
    buy2 = decision("b2", "2026-09-09T14:00:00Z", Action.BUY, "META", 100.0)
    state = rebuild_effective_portfolio([buy1, buy2], [eval1])
    assert state.positions["META"].decision_id == "b2"
    assert state.cash_eur == 902.0
    assert state.equity_eur == 1002.0


def test_pyramiding_is_blocked_against_effective_state():
    buy = decision("b1", "2026-09-07T14:00:00Z", Action.BUY, "META", 100.0)
    state = rebuild_effective_portfolio([buy], [])
    candidate = decision("b2", "2026-09-08T14:00:00Z", Action.BUY, "META", 100.0)
    with pytest.raises(ValueError, match="pyramiding"):
        validate_decision_against_effective_portfolio(candidate, state)


def test_hold_and_sell_require_an_open_position():
    state = rebuild_effective_portfolio([], [])
    for action in (Action.HOLD, Action.SELL):
        candidate = decision("x", "2026-09-08T14:00:00Z", action, "META", 0.0)
        with pytest.raises(ValueError, match="effective open position"):
            validate_decision_against_effective_portfolio(candidate, state)


def test_total_exposure_guard_uses_current_equity():
    buys = [
        decision("b1", "2026-09-07T14:00:00Z", Action.BUY, "META", 150.0),
        decision("b2", "2026-09-07T15:00:00Z", Action.BUY, "AMD", 150.0),
    ]
    state = rebuild_effective_portfolio(buys, [])
    candidate = decision("b3", "2026-09-08T14:00:00Z", Action.BUY, "MSFT", 150.0)
    validate_decision_against_effective_portfolio(candidate, state)
    too_much = decision("b4", "2026-09-08T14:00:00Z", Action.BUY, "NVDA", 151.0)
    with pytest.raises(ValueError):
        validate_decision_against_effective_portfolio(too_much, state)
