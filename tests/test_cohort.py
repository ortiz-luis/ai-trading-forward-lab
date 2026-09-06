import json

import pytest

from engine.cohort import CohortStartBlocked, load_cohort, validate_start_prerequisites


FREEZE = {
    "cohort_id": "forward-v1",
    "status": "ARMED_NOT_STARTED",
    "starting_capital_eur": 1000.0,
    "protocol_version": "v1",
    "prompt_version": "trading-v1",
    "model": "gpt-5.6-terra",
    "market_provider": "alpaca-market-data",
    "evidence_policy": {"max_items": 12},
    "decision_schedule": "16:17 Monday-Friday",
    "timezone": "Europe/Paris",
    "frozen_components": {
        "prompt": "a",
        "protocol": "b",
        "evidence": "c",
        "openai_provider": "d",
        "market_provider": "e",
        "evaluator": "f",
    },
    "started_at": None,
    "observation_count": 0,
}


def write_freeze(tmp_path):
    path = tmp_path / "cohort.json"
    path.write_text(json.dumps(FREEZE), encoding="utf-8")
    return path


def test_armed_freeze_validates(tmp_path):
    cohort = load_cohort(write_freeze(tmp_path))
    assert cohort.status == "ARMED_NOT_STARTED"
    assert cohort.starting_capital_eur == 1000.0


def test_start_blocked_without_runtime_context(tmp_path):
    with pytest.raises(CohortStartBlocked, match="runtime_context"):
        validate_start_prerequisites(
            cohort_path=write_freeze(tmp_path),
            runtime_context_path=tmp_path / "runtime_context.json",
            decisions_path=tmp_path / "decisions.jsonl",
            env={"OPENAI_API_KEY": "x", "ALPACA_API_KEY": "y", "ALPACA_API_SECRET": "z"},
        )


def test_start_blocked_without_secrets(tmp_path):
    context = tmp_path / "runtime_context.json"
    context.write_text("{}", encoding="utf-8")
    with pytest.raises(CohortStartBlocked, match="OPENAI_API_KEY"):
        validate_start_prerequisites(
            cohort_path=write_freeze(tmp_path),
            runtime_context_path=context,
            decisions_path=tmp_path / "decisions.jsonl",
            env={},
        )


def test_start_blocked_on_existing_history(tmp_path):
    context = tmp_path / "runtime_context.json"
    context.write_text("{}", encoding="utf-8")
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text('{"decision_id":"old"}\n', encoding="utf-8")
    with pytest.raises(CohortStartBlocked, match="existing decisions"):
        validate_start_prerequisites(
            cohort_path=write_freeze(tmp_path),
            runtime_context_path=context,
            decisions_path=decisions,
            env={"OPENAI_API_KEY": "x", "ALPACA_API_KEY": "y", "ALPACA_API_SECRET": "z"},
        )


def test_start_prerequisites_pass_only_when_all_inputs_exist(tmp_path):
    context = tmp_path / "runtime_context.json"
    context.write_text("{}", encoding="utf-8")
    cohort = validate_start_prerequisites(
        cohort_path=write_freeze(tmp_path),
        runtime_context_path=context,
        decisions_path=tmp_path / "decisions.jsonl",
        env={"OPENAI_API_KEY": "x", "ALPACA_API_KEY": "y", "ALPACA_API_SECRET": "z"},
    )
    assert cohort.cohort_id == "forward-v1"
