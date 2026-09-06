import json

from engine import automation_runner
from engine.ledger import append_jsonl, make_idempotency_key
from engine.schemas import Action, DecisionEvent


def _decision_payload():
    return DecisionEvent(
        decision_id="d1",
        idempotency_key="k1",
        decision_at="2026-09-07T14:00:00Z",
        cutoff_at="2026-09-07T13:59:00Z",
        action=Action.BUY,
        symbol="META",
        notional_eur=100.0,
        confidence=0.7,
        horizon_days=5,
        stop_pct=-0.02,
        thesis="fixture",
        counter_thesis="fixture",
        prompt_version="trading-v1",
        model="fixture",
        sources_hash="fixture",
    ).to_dict()


def _redirect_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(automation_runner, "DATA_DIR", tmp_path)
    monkeypatch.setattr(automation_runner, "DECISIONS", tmp_path / "decisions.jsonl")
    monkeypatch.setattr(automation_runner, "EVALUATIONS", tmp_path / "evaluations.jsonl")
    monkeypatch.setattr(automation_runner, "SYSTEM_EVENTS", tmp_path / "system_events.jsonl")
    monkeypatch.setattr(automation_runner, "HEALTH", tmp_path / "health.json")


def test_decision_runner_skips_existing_session_before_secrets(monkeypatch, tmp_path):
    _redirect_paths(monkeypatch, tmp_path)
    monkeypatch.setenv("AITFL_SESSION_DATE", "2026-09-07")
    key = make_idempotency_key("2026-09-07", "v1")
    append_jsonl(automation_runner.DECISIONS, {"decision_id": "existing", "idempotency_key": key})
    assert automation_runner.run_decision_cycle() == 0
    assert not automation_runner.SYSTEM_EVENTS.exists()


def test_missing_runtime_secrets_fail_closed(monkeypatch, tmp_path):
    _redirect_paths(monkeypatch, tmp_path)
    monkeypatch.setenv("AITFL_SESSION_DATE", "2026-09-08")
    for name in ("OPENAI_API_KEY", "ALPACA_API_KEY", "ALPACA_API_SECRET"):
        monkeypatch.delenv(name, raising=False)
    assert automation_runner.run_decision_cycle() == 0
    text = automation_runner.SYSTEM_EVENTS.read_text(encoding="utf-8")
    assert "DATA_ERROR" in text
    assert "OPENAI_API_KEY" in text
    assert not automation_runner.DECISIONS.exists()


def test_evaluation_runner_persists_once(monkeypatch, tmp_path):
    _redirect_paths(monkeypatch, tmp_path)
    payload = {
        "decision": _decision_payload(),
        "asset_prices": [
            {"observed_at": "2026-09-07T14:01:00Z", "price": 100.0},
            {"observed_at": "2026-09-08T14:00:00Z", "price": 104.0},
        ],
        "benchmark_prices": [
            {"observed_at": "2026-09-07T14:01:00Z", "price": 100.0},
            {"observed_at": "2026-09-08T14:00:00Z", "price": 101.0},
        ],
        "rules": {"simulated_cost_bps": 5.0, "slippage_bps": 5.0},
    }
    (tmp_path / "evaluation_input.json").write_text(json.dumps(payload), encoding="utf-8")
    assert automation_runner.run_evaluation_cycle() == 0
    assert automation_runner.run_evaluation_cycle() == 0
    rows = [json.loads(line) for line in automation_runner.EVALUATIONS.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["decision_id"] == "d1"
