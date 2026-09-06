from pathlib import Path

from engine.automation import (
    HealthState,
    decision_already_exists,
    mark_decision_success,
    mark_evaluation_success,
    read_health,
    run_guarded_step,
    write_health,
)
from engine.ledger import append_jsonl, make_idempotency_key


def test_same_session_is_idempotent(tmp_path):
    ledger = tmp_path / "decisions.jsonl"
    key = make_idempotency_key("2026-09-07", "v1")
    append_jsonl(ledger, {"decision_id": "d1", "idempotency_key": key})
    assert decision_already_exists(ledger, session_date="2026-09-07")
    assert not decision_already_exists(ledger, session_date="2026-09-08")


def test_health_round_trip_and_success_markers(tmp_path):
    health = tmp_path / "health.json"
    write_health(health, HealthState(status="HEALTHY", updated_at="2026-09-07T10:00:00Z"))
    mark_decision_success(health, at="2026-09-07T14:00:00Z")
    state = read_health(health)
    assert state is not None
    assert state.last_decision_at == "2026-09-07T14:00:00Z"
    mark_evaluation_success(health, at="2026-09-07T15:00:00Z")
    state = read_health(health)
    assert state.last_evaluation_at == "2026-09-07T15:00:00Z"
    assert state.last_decision_at == "2026-09-07T14:00:00Z"


def test_guarded_failure_is_explicit_and_does_not_raise(tmp_path):
    health = tmp_path / "health.json"
    events = tmp_path / "system_events.jsonl"

    def boom():
        raise RuntimeError("fixture outage")

    result = run_guarded_step(
        step_name="market",
        callback=boom,
        health_path=health,
        system_events_path=events,
        error_kind="DATA_ERROR",
    )
    assert result is None
    state = read_health(health)
    assert state.status == "DEGRADED"
    assert state.last_error_kind == "DATA_ERROR"
    assert "fixture outage" in events.read_text(encoding="utf-8")


def test_multiday_failures_do_not_corrupt_prior_health_success(tmp_path):
    health = tmp_path / "health.json"
    events = tmp_path / "system_events.jsonl"
    mark_decision_success(health, at="2026-09-07T14:00:00Z")

    for kind in ("DATA_ERROR", "AI_ERROR", "DEPLOY_ERROR"):
        run_guarded_step(
            step_name=kind.lower(),
            callback=lambda: (_ for _ in ()).throw(RuntimeError(kind)),
            health_path=health,
            system_events_path=events,
            error_kind=kind,
        )

    state = read_health(health)
    assert state.last_decision_at == "2026-09-07T14:00:00Z"
    assert state.status == "DEGRADED"
    text = events.read_text(encoding="utf-8")
    for kind in ("DATA_ERROR", "AI_ERROR", "DEPLOY_ERROR"):
        assert kind in text
