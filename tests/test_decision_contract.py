import pytest

from engine.decision_contract import DecisionInput, DecisionOutput, build_prompt_input
from engine.schemas import Action
from engine.trading_protocol import PROTOCOL_V1


def valid_buy_payload():
    return {
        "action": "BUY",
        "symbol": "META",
        "notional_eur": 100,
        "confidence": 0.72,
        "horizon_days": 5,
        "stop_pct": -0.02,
        "thesis": "fixture thesis",
        "counter_thesis": "fixture counter",
        "sources": [{"url": "https://example.com/source", "published_at": "2026-09-06T12:00:00Z"}],
    }


def test_valid_buy_contract():
    out = DecisionOutput.from_dict(valid_buy_payload())
    assert out.action == Action.BUY
    assert out.symbol == "META"


def test_no_trade_contract():
    payload = valid_buy_payload()
    payload.update({
        "action": "NO_TRADE",
        "symbol": None,
        "notional_eur": 0,
        "horizon_days": 0,
        "stop_pct": None,
    })
    out = DecisionOutput.from_dict(payload)
    assert out.action == Action.NO_TRADE


def test_extra_field_fails_closed():
    payload = valid_buy_payload()
    payload["commentary"] = "should fail"
    with pytest.raises(ValueError, match="decision keys mismatch"):
        DecisionOutput.from_dict(payload)


def test_invalid_symbol_fails_protocol():
    payload = valid_buy_payload()
    payload["symbol"] = "NOTALLOWED"
    with pytest.raises(ValueError):
        DecisionOutput.from_dict(payload)


def test_invalid_stop_fails_protocol():
    payload = valid_buy_payload()
    payload["stop_pct"] = -0.20
    with pytest.raises(ValueError):
        DecisionOutput.from_dict(payload)


def test_prompt_input_contains_cutoff_portfolio_and_context():
    payload = build_prompt_input(DecisionInput(
        cutoff_at="2026-09-06T14:00:00Z",
        portfolio={"cash_eur": 1000},
        protocol={"version": PROTOCOL_V1.version},
        market={"META": {"price": 100}},
        evidence=[{"url": "https://example.com", "published_at": "2026-09-06T12:00:00Z"}],
    ))
    assert payload["cutoff_at"] == "2026-09-06T14:00:00Z"
    assert payload["portfolio"]["cash_eur"] == 1000
    assert payload["prompt_version"] == "trading-v1"
