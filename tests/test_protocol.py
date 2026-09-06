from dataclasses import replace

import pytest

from engine.protocol import PROTOCOL_V1
from engine.schemas import Action, DecisionEvent


def event(action=Action.BUY, symbol="META", notional=100.0, horizon=5, stop=-0.02):
    return DecisionEvent(
        decision_id="d1",
        idempotency_key="k1",
        decision_at="2026-09-06T15:00:00Z",
        cutoff_at="2026-09-06T14:59:00Z",
        action=action,
        symbol=symbol,
        notional_eur=notional,
        confidence=0.75,
        horizon_days=horizon,
        stop_pct=stop,
        thesis="fixture",
        counter_thesis="fixture counter",
        prompt_version="v1",
        model="fixture",
        sources_hash="fixture",
    )


def test_protocol_v1_is_self_consistent():
    PROTOCOL_V1.validate()
    assert PROTOCOL_V1.benchmark_symbol == "SPY"
    assert "SPY" not in PROTOCOL_V1.tradable_universe


def test_valid_buy_passes():
    PROTOCOL_V1.validate_decision(event(), current_equity_eur=1000)


def test_symbol_outside_universe_fails():
    with pytest.raises(ValueError, match="outside tradable universe"):
        PROTOCOL_V1.validate_decision(event(symbol="TSLA"), current_equity_eur=1000)


def test_position_size_cap_fails_closed():
    with pytest.raises(ValueError, match="max_position_pct"):
        PROTOCOL_V1.validate_decision(event(notional=151), current_equity_eur=1000)


def test_stop_and_horizon_bounds_are_enforced():
    with pytest.raises(ValueError, match="stop"):
        PROTOCOL_V1.validate_decision(event(stop=-0.08), current_equity_eur=1000)
    with pytest.raises(ValueError, match="horizon"):
        PROTOCOL_V1.validate_decision(event(horizon=11), current_equity_eur=1000)


def test_no_trade_is_zero_allocation():
    nt = event(action=Action.NO_TRADE, symbol=None, notional=0, horizon=0, stop=None)
    PROTOCOL_V1.validate_decision(nt, current_equity_eur=1000)


def test_low_equity_adapts_minimum_notional_without_breaking_15pct_cap():
    tiny = event(notional=45)
    PROTOCOL_V1.validate_decision(tiny, current_equity_eur=300)
