from __future__ import annotations

from dataclasses import dataclass
import json

import pytest

from engine.decision_contract import DecisionInput
from engine.providers.openai_decision import DecisionProviderError, OpenAIDecisionProvider


@dataclass
class FakeUsage:
    input_tokens: int = 100
    output_tokens: int = 40
    total_tokens: int = 140


@dataclass
class FakeResponse:
    output_text: str
    status: str = "completed"
    id: str = "resp_fixture"
    model: str = "gpt-5.6-terra"
    usage: FakeUsage | None = None


class FakeResponses:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if not self._responses:
            raise RuntimeError("no fake responses left")
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


def input_fixture() -> DecisionInput:
    return DecisionInput(
        cutoff_at="2026-09-06T14:00:00Z",
        portfolio={"cash_eur": 1000, "equity_eur": 1000, "positions": {}},
        protocol={"version": "v1"},
        market={"META": {"price": 100.0}},
        evidence=[{"url": "https://example.com/source", "published_at": "2026-09-06T12:00:00Z"}],
    )


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


def valid_buy_json() -> str:
    return json.dumps(valid_buy_payload())


def test_valid_response_returns_decision_and_usage():
    fake = FakeClient([FakeResponse(valid_buy_json(), usage=FakeUsage())])
    provider = OpenAIDecisionProvider(client=fake, model="gpt-5.6-terra")
    result = provider.decide(input_fixture(), instructions="fixture")
    assert result.ok
    assert result.decision.symbol == "META"
    assert result.total_tokens == 140
    assert result.repaired is False
    call = fake.responses.calls[0]
    assert call["store"] is False
    assert call["text"]["format"]["type"] == "json_schema"
    assert call["text"]["format"]["strict"] is True


def test_invalid_first_response_gets_one_repair_attempt():
    fake = FakeClient([
        FakeResponse("not-json"),
        FakeResponse(valid_buy_json(), id="resp_repaired"),
    ])
    provider = OpenAIDecisionProvider(client=fake)
    result = provider.decide(input_fixture(), instructions="fixture")
    assert result.ok
    assert result.repaired is True
    assert len(fake.responses.calls) == 2


def test_two_failures_return_explicit_ai_error_not_no_trade():
    fake = FakeClient([RuntimeError("network down"), RuntimeError("still down")])
    provider = OpenAIDecisionProvider(client=fake)
    result = provider.decide(input_fixture(), instructions="fixture")
    assert result.ok is False
    assert result.decision is None
    assert result.error_code == "AI_ERROR"
    assert len(fake.responses.calls) == 2


def test_protocol_invalid_output_fails_closed_after_single_repair():
    invalid = valid_buy_payload()
    invalid["notional_eur"] = 999
    fake = FakeClient([FakeResponse(json.dumps(invalid)), FakeResponse(json.dumps(invalid))])
    provider = OpenAIDecisionProvider(client=fake)
    result = provider.decide(input_fixture(), instructions="fixture")
    assert result.error_code == "AI_ERROR"
    assert result.decision is None


def test_invented_source_fails_closed_even_when_schema_is_valid():
    invalid = valid_buy_payload()
    invalid["sources"] = [{"url":"https://invented.example/news","published_at":"2026-09-06T12:00:00Z"}]
    fake = FakeClient([FakeResponse(json.dumps(invalid)), FakeResponse(json.dumps(invalid))])
    result = OpenAIDecisionProvider(client=fake).decide(input_fixture(), instructions="fixture")
    assert result.error_code == "AI_ERROR"
    assert result.decision is None


def test_missing_key_fails_before_network(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(DecisionProviderError, match="OPENAI_API_KEY"):
        OpenAIDecisionProvider()


def test_model_can_be_selected_from_environment(monkeypatch):
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.6-sol")
    fake = FakeClient([FakeResponse(valid_buy_json())])
    provider = OpenAIDecisionProvider(client=fake)
    assert provider.model == "gpt-5.6-sol"
