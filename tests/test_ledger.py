from __future__ import annotations

from dataclasses import replace

import pytest

from engine.ledger import (
    append_decision,
    make_decision_id,
    make_idempotency_key,
    read_jsonl,
    verify_locked_hash,
)
from engine.schemas import Action, DecisionEvent, EvaluationEvent, SystemEvent, SystemEventKind, paris_display


def sample_decision() -> DecisionEvent:
    key = make_idempotency_key("2026-09-06", "v1")
    return DecisionEvent(
        decision_id=make_decision_id(key),
        idempotency_key=key,
        decision_at="2026-09-06T14:17:00Z",
        cutoff_at="2026-09-06T14:15:00Z",
        action=Action.BUY,
        symbol="META",
        notional_eur=120.0,
        confidence=0.74,
        horizon_days=5,
        stop_pct=-0.02,
        thesis="Fresh catalyst plus acceptable momentum.",
        counter_thesis="Initial reaction could reverse.",
        prompt_version="v1",
        model="fixture-model",
        sources_hash="sources-fixture",
    )


def test_decision_round_trip_and_hash(tmp_path):
    path = tmp_path / "decisions.jsonl"
    locked = append_decision(path, sample_decision())
    assert verify_locked_hash(locked)
    rows = list(read_jsonl(path))
    assert len(rows) == 1
    restored = DecisionEvent.from_dict(rows[0])
    assert restored == locked
    assert paris_display(restored.decision_at).startswith("2026-09-06T16:17:00+02:00")


def test_duplicate_decision_rejected(tmp_path):
    path = tmp_path / "decisions.jsonl"
    event = sample_decision()
    append_decision(path, event)
    with pytest.raises(ValueError, match="duplicate decision_id"):
        append_decision(path, event)


def test_locked_payload_detects_mutation(tmp_path):
    locked = append_decision(tmp_path / "decisions.jsonl", sample_decision())
    tampered = replace(locked, notional_eur=999.0)
    assert not verify_locked_hash(tampered)


def test_strict_schema_rejects_unknown_field():
    payload = sample_decision().to_dict()
    payload["surprise_future_field"] = True
    with pytest.raises(ValueError, match="unknown fields"):
        DecisionEvent.from_dict(payload)


def test_other_event_schemas_round_trip():
    evaluation = EvaluationEvent(
        evaluation_id="eval-1",
        decision_id="decision-1",
        evaluated_at="2026-09-07T15:00:00Z",
        exit_reason="horizon",
        exit_price=110.0,
        gross_pnl_eur=4.0,
        costs_eur=0.2,
        net_pnl_eur=3.8,
        benchmark_return_pct=0.5,
    )
    assert EvaluationEvent.from_dict(evaluation.to_dict()) == evaluation

    system = SystemEvent(
        system_event_id="sys-1",
        occurred_at="2026-09-07T15:00:00Z",
        kind=SystemEventKind.DATA_ERROR,
        message="fixture failure",
        details={"provider": "fixture"},
    )
    assert SystemEvent.from_dict(system.to_dict()) == system


def test_no_trade_must_not_allocate_capital():
    event = replace(sample_decision(), action=Action.NO_TRADE, symbol=None, notional_eur=1.0)
    with pytest.raises(ValueError, match="NO_TRADE"):
        event.validate()
