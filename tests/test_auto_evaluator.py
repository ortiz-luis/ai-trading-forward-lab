from engine.auto_evaluator import run_unattended_evaluations
from engine.ledger import append_decision, read_jsonl
from engine.providers.fixture import FixtureMarketDataProvider
from engine.providers.market import MarketCandle
from engine.schemas import Action, DecisionEvent


def decision(horizon=2, stop=-0.02):
    return DecisionEvent(
        decision_id="b1",
        idempotency_key="k1",
        decision_at="2026-09-07T14:00:00Z",
        cutoff_at="2026-09-07T13:59:00Z",
        action=Action.BUY,
        symbol="META",
        notional_eur=100.0,
        confidence=0.7,
        horizon_days=horizon,
        stop_pct=stop,
        thesis="fixture",
        counter_thesis="fixture",
        prompt_version="trading-v1",
        model="fixture",
        sources_hash="fixture",
    )


def c(symbol, start, end, close):
    return MarketCandle(
        symbol=symbol,
        start_at=start,
        end_at=end,
        open=close,
        high=close + 0.1,
        low=close - 0.1,
        close=close,
        volume=1000,
        currency="USD",
    )


def provider(two_days=True, stop=False):
    meta = [
        c("META", "2026-09-07T14:00:00Z", "2026-09-07T14:01:00Z", 100.0),
        c("META", "2026-09-07T19:59:00Z", "2026-09-07T20:00:00Z", 101.0),
    ]
    spy = [
        c("SPY", "2026-09-07T14:00:00Z", "2026-09-07T14:01:00Z", 500.0),
        c("SPY", "2026-09-07T19:59:00Z", "2026-09-07T20:00:00Z", 501.0),
    ]
    if stop:
        meta[1] = c("META", "2026-09-07T19:59:00Z", "2026-09-07T20:00:00Z", 97.0)
    if two_days:
        meta += [
            c("META", "2026-09-08T14:00:00Z", "2026-09-08T14:01:00Z", 102.0),
            c("META", "2026-09-08T19:59:00Z", "2026-09-08T20:00:00Z", 104.0),
        ]
        spy += [
            c("SPY", "2026-09-08T14:00:00Z", "2026-09-08T14:01:00Z", 502.0),
            c("SPY", "2026-09-08T19:59:00Z", "2026-09-08T20:00:00Z", 503.0),
        ]
    return FixtureMarketDataProvider(candles={"META": meta, "SPY": spy})


def test_horizon_evaluation_created_once(tmp_path):
    decisions = tmp_path / "decisions.jsonl"
    evaluations = tmp_path / "evaluations.jsonl"
    append_decision(decisions, decision())
    kwargs = dict(
        provider=provider(),
        decisions_path=decisions,
        evaluations_path=evaluations,
        system_events_path=tmp_path / "system.jsonl",
        health_path=tmp_path / "health.json",
    )
    assert run_unattended_evaluations(**kwargs) == 1
    assert run_unattended_evaluations(**kwargs) == 0
    rows = list(read_jsonl(evaluations))
    assert len(rows) == 1
    assert rows[0]["exit_reason"] == "horizon"


def test_stop_can_close_before_horizon(tmp_path):
    decisions = tmp_path / "decisions.jsonl"
    evaluations = tmp_path / "evaluations.jsonl"
    append_decision(decisions, decision(horizon=5))
    created = run_unattended_evaluations(
        provider=provider(two_days=False, stop=True),
        decisions_path=decisions,
        evaluations_path=evaluations,
        system_events_path=tmp_path / "system.jsonl",
        health_path=tmp_path / "health.json",
    )
    assert created == 1
    assert list(read_jsonl(evaluations))[0]["exit_reason"] == "stop"


def test_not_ready_is_noop_not_error(tmp_path):
    decisions = tmp_path / "decisions.jsonl"
    append_decision(decisions, decision(horizon=5))
    assert run_unattended_evaluations(
        provider=provider(two_days=False),
        decisions_path=decisions,
        evaluations_path=tmp_path / "evaluations.jsonl",
        system_events_path=tmp_path / "system.jsonl",
        health_path=tmp_path / "health.json",
    ) == 0
    assert not (tmp_path / "system.jsonl").exists()
