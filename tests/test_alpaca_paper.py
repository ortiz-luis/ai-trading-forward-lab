import pytest

from engine.providers.alpaca_paper import AlpacaPaperShadow, PAPER_BASE_URL, PaperShadowError
from engine.schemas import Action, DecisionEvent


def decision(action=Action.BUY, notional=100.0):
    return DecisionEvent(
        decision_id="d-paper",
        idempotency_key="k-paper",
        decision_at="2026-09-06T14:00:00Z",
        cutoff_at="2026-09-06T13:59:00Z",
        action=action,
        symbol="META" if action != Action.NO_TRADE else None,
        notional_eur=notional if action == Action.BUY else 0.0,
        confidence=0.7,
        horizon_days=5 if action == Action.BUY else 0,
        stop_pct=-0.02 if action == Action.BUY else None,
        thesis="fixture",
        counter_thesis="fixture",
        prompt_version="v1",
        model="fixture",
        sources_hash="fixture",
    )


def test_live_endpoint_is_hard_blocked():
    with pytest.raises(PaperShadowError, match="forbidden"):
        AlpacaPaperShadow(api_key="x", api_secret="y", base_url="https://api.alpaca.markets")


def test_paper_endpoint_is_fixed():
    shadow = AlpacaPaperShadow(api_key="x", api_secret="y", base_url=PAPER_BASE_URL)
    assert shadow.base_url == PAPER_BASE_URL


def test_no_trade_and_hold_do_not_create_paper_orders(monkeypatch):
    shadow = AlpacaPaperShadow(api_key="x", api_secret="y")
    monkeypatch.setattr(shadow, "_json_request", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network should not be called")))
    assert shadow.mirror_decision(decision(Action.NO_TRADE, 0), reference_price_usd=100) is None
    hold = decision(Action.HOLD, 0)
    assert shadow.mirror_decision(hold, reference_price_usd=100) is None


def test_buy_mirror_is_normalized(monkeypatch):
    shadow = AlpacaPaperShadow(api_key="x", api_secret="y")
    seen = {}
    def fake(method, path, payload):
        seen.update({"method": method, "path": path, "payload": payload})
        return {"id":"o1","symbol":"META","side":"buy","status":"filled","filled_qty":"1.0","filled_avg_price":"100.0"}
    monkeypatch.setattr(shadow, "_json_request", fake)
    fill = shadow.mirror_decision(decision(), reference_price_usd=100)
    assert seen["path"] == "/v2/orders"
    assert seen["payload"]["side"] == "buy"
    assert fill.order_id == "o1"
    assert fill.filled_avg_price == 100.0
