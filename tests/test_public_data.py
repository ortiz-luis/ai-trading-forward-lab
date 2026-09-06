import json

import pytest

from engine.public_data import assert_public_safe, build_public_dashboard
from engine.ledger import append_decision, append_jsonl
from engine.schemas import Action, DecisionEvent, EvaluationEvent


def decision(action=Action.BUY, symbol="META", notional=100.0, decision_id="d1"):
    return DecisionEvent(
        decision_id=decision_id,
        idempotency_key=f"k-{decision_id}",
        decision_at="2026-09-06T14:00:00Z",
        cutoff_at="2026-09-06T13:59:00Z",
        action=action,
        symbol=symbol,
        notional_eur=notional,
        confidence=0.72,
        horizon_days=5 if action == Action.BUY else 0,
        stop_pct=-0.02 if action == Action.BUY else None,
        thesis="fixture thesis",
        counter_thesis="fixture counter",
        prompt_version="v1",
        model="fixture-model",
        sources_hash="fixture-sources",
    )


def test_public_dashboard_contains_only_ui_fields(tmp_path):
    decisions=tmp_path/"decisions.jsonl"
    evaluations=tmp_path/"evaluations.jsonl"
    health=tmp_path/"health.json"
    output=tmp_path/"public"/"dashboard.json"

    append_decision(decisions, decision())
    evaluation=EvaluationEvent(
        evaluation_id="e1",
        decision_id="d1",
        evaluated_at="2026-09-08T14:00:00Z",
        exit_reason="horizon",
        exit_price=105.0,
        gross_pnl_eur=5.0,
        costs_eur=0.2,
        net_pnl_eur=4.8,
        benchmark_return_pct=1.0,
    )
    append_jsonl(evaluations, evaluation.to_dict(), unique_key="evaluation_id")
    health.write_text(json.dumps({"last_decision_success_at":"2026-09-06T14:01:00Z","private_debug":"do-not-publish"}),encoding="utf-8")

    payload=build_public_dashboard(decisions_path=decisions,evaluations_path=evaluations,health_path=health,output_path=output)
    text=output.read_text(encoding="utf-8")

    assert payload["starting_capital_eur"] == 1000.0
    assert payload["current_equity_eur"] == 1004.8
    assert payload["counts"]["wins"] == 1
    assert payload["latest_decision"]["symbol"] == "META"
    assert "private_debug" not in text
    assert "sources_hash" not in text
    assert "locked_payload_hash" not in text


def test_secret_pattern_scan_fails_closed():
    with pytest.raises(ValueError):
        assert_public_safe('{"OPENAI_API_KEY":"should-never-publish"}')


def test_empty_dashboard_is_valid(tmp_path):
    output=tmp_path/"dashboard.json"
    payload=build_public_dashboard(
        decisions_path=tmp_path/"missing-decisions.jsonl",
        evaluations_path=tmp_path/"missing-evaluations.jsonl",
        health_path=tmp_path/"missing-health.json",
        output_path=output,
    )
    assert payload["current_equity_eur"] == 1000.0
    assert payload["latest_decision"] is None
    assert payload["history"] == []
