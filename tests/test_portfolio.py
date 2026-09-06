import pytest

from engine.ledger import append_decision
from engine.portfolio import (
    PortfolioRules,
    PortfolioState,
    apply_decision,
    rebuild_portfolio,
    rebuild_portfolio_from_ledger,
)
from engine.schemas import Action, DecisionEvent


def decision(action: Action, symbol: str | None, notional: float, n: int) -> DecisionEvent:
    return DecisionEvent(
        decision_id=f"d{n}",
        idempotency_key=f"k{n}",
        decision_at=f"2026-09-0{n}T14:00:00Z",
        cutoff_at=f"2026-09-0{n}T13:59:00Z",
        action=action,
        symbol=symbol,
        notional_eur=notional,
        confidence=0.7,
        horizon_days=5,
        stop_pct=-0.02 if action == Action.BUY else None,
        thesis="fixture thesis",
        counter_thesis="fixture counter",
        prompt_version="v1",
        model="fixture",
        sources_hash="sources",
    )


def test_initial_state_is_all_cash():
    state = PortfolioState.initial(1000)
    assert state.cash_eur == 1000
    assert state.equity_eur == 1000
    assert state.exposure_eur == 0


def test_buy_hold_sell_round_trip_preserves_cost_basis_equity():
    rules = PortfolioRules(max_position_pct=0.20, max_total_exposure_pct=0.50, max_open_positions=3)
    s0 = PortfolioState.initial(1000)
    s1 = apply_decision(s0, decision(Action.BUY, "META", 150, 1), rules)
    assert s1.cash_eur == 850
    assert s1.exposure_eur == 150
    assert s1.equity_eur == 1000

    s2 = apply_decision(s1, decision(Action.HOLD, "META", 0, 2), rules)
    assert s2.cash_eur == 850
    assert s2.exposure_eur == 150

    s3 = apply_decision(s2, decision(Action.SELL, "META", 0, 3), rules)
    assert s3.cash_eur == 1000
    assert s3.exposure_eur == 0
    assert s3.equity_eur == 1000


def test_no_trade_is_noop():
    rules = PortfolioRules()
    state = PortfolioState.initial(1000)
    result = apply_decision(state, decision(Action.NO_TRADE, None, 0, 1), rules)
    assert result.cash_eur == state.cash_eur
    assert result.positions == state.positions


def test_limits_block_oversized_position():
    rules = PortfolioRules(max_position_pct=0.15, max_total_exposure_pct=0.45, max_open_positions=3)
    with pytest.raises(ValueError, match="max_position_pct"):
        apply_decision(PortfolioState.initial(1000), decision(Action.BUY, "META", 200, 1), rules)


def test_limits_block_too_many_positions_and_total_exposure():
    rules = PortfolioRules(max_position_pct=0.20, max_total_exposure_pct=0.40, max_open_positions=2)
    s = PortfolioState.initial(1000)
    s = apply_decision(s, decision(Action.BUY, "META", 150, 1), rules)
    s = apply_decision(s, decision(Action.BUY, "AMD", 150, 2), rules)
    with pytest.raises(ValueError):
        apply_decision(s, decision(Action.BUY, "MSFT", 100, 3), rules)


def test_rebuild_is_deterministic():
    rules = PortfolioRules(max_position_pct=0.20, max_total_exposure_pct=0.50, max_open_positions=3)
    events = [
        decision(Action.BUY, "META", 150, 1),
        decision(Action.NO_TRADE, None, 0, 2),
        decision(Action.HOLD, "META", 0, 3),
    ]
    a = rebuild_portfolio(events, starting_capital_eur=1000, rules=rules)
    b = rebuild_portfolio(events, starting_capital_eur=1000, rules=rules)
    assert a.to_dict() == b.to_dict()


def test_rebuild_from_ledger_matches_in_memory_rebuild(tmp_path):
    rules = PortfolioRules(max_position_pct=0.20, max_total_exposure_pct=0.50, max_open_positions=3)
    path = tmp_path / "decisions.jsonl"
    events = [
        decision(Action.BUY, "META", 150, 1),
        decision(Action.NO_TRADE, None, 0, 2),
        decision(Action.HOLD, "META", 0, 3),
    ]
    for event in events:
        append_decision(path, event)
    direct = rebuild_portfolio(events, starting_capital_eur=1000, rules=rules)
    from_ledger = rebuild_portfolio_from_ledger(path, starting_capital_eur=1000, rules=rules)
    assert direct.to_dict() == from_ledger.to_dict()
