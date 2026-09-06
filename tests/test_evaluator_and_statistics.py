from engine.evaluator import EvaluationRules, PricePoint, evaluate_long_decision, to_evaluation_event
from engine.statistics import ConfidenceObservation, build_statistics
from engine.schemas import Action, DecisionEvent


def buy_decision(stop=-0.02):
    return DecisionEvent(
        decision_id="d1",
        idempotency_key="k1",
        decision_at="2026-09-06T14:00:00Z",
        cutoff_at="2026-09-06T13:59:00Z",
        action=Action.BUY,
        symbol="META",
        notional_eur=100.0,
        confidence=0.7,
        horizon_days=5,
        stop_pct=stop,
        thesis="fixture",
        counter_thesis="fixture",
        prompt_version="v1",
        model="fixture",
        sources_hash="fixture",
    )


def p(price, n):
    return PricePoint(f"2026-09-0{n}T14:00:00Z", price)


def test_horizon_win_with_costs_and_benchmark():
    result = evaluate_long_decision(
        buy_decision(),
        asset_prices=[p(100,1), p(102,2), p(105,3)],
        benchmark_prices=[p(100,1), p(100.5,2), p(101,3)],
        rules=EvaluationRules(simulated_cost_bps=5, slippage_bps=5),
    )
    assert result.exit_reason == "horizon"
    assert result.net_pnl_eur > 0
    assert round(result.benchmark_return_pct, 6) == 1.0


def test_stop_loss_closes_early_and_benchmark_uses_same_window():
    result = evaluate_long_decision(
        buy_decision(stop=-0.02),
        asset_prices=[p(100,1), p(97,2), p(110,3)],
        benchmark_prices=[p(100,1), p(99,2), p(105,3)],
    )
    assert result.exit_reason == "stop"
    assert result.net_pnl_eur < 0
    assert round(result.benchmark_return_pct, 6) == -1.0


def test_explicit_sell_closes_before_horizon():
    result = evaluate_long_decision(
        buy_decision(),
        asset_prices=[p(100,1), p(103,2), p(106,3)],
        benchmark_prices=[p(100,1), p(101,2), p(104,3)],
        explicit_sell_index=1,
    )
    assert result.exit_reason == "explicit_sell"
    assert round(result.benchmark_return_pct, 6) == 1.0


def test_evaluation_event_is_separate_from_decision():
    decision = buy_decision()
    result = evaluate_long_decision(
        decision,
        asset_prices=[p(100,1), p(105,3)],
        benchmark_prices=[p(100,1), p(101,3)],
    )
    event = to_evaluation_event(result, evaluation_id="e1", decision_id=decision.decision_id, evaluated_at="2026-09-08T14:00:00Z")
    assert event.decision_id == decision.decision_id
    assert decision.locked_payload_hash == ""


def test_statistics_track_money_drawdown_score_and_calibration_separately():
    d = buy_decision()
    win = to_evaluation_event(
        evaluate_long_decision(d, asset_prices=[p(100,1), p(110,3)], benchmark_prices=[p(100,1), p(101,3)]),
        evaluation_id="e1", decision_id="d1", evaluated_at="2026-09-08T14:00:00Z"
    )
    loss = to_evaluation_event(
        evaluate_long_decision(d, asset_prices=[p(100,1), p(90,3)], benchmark_prices=[p(100,1), p(99,3)]),
        evaluation_id="e2", decision_id="d2", evaluated_at="2026-09-09T14:00:00Z"
    )
    stats = build_statistics(
        [win, loss],
        starting_capital_eur=1000,
        no_trades=2,
        errors=1,
        confidence_observations=[
            ConfidenceObservation(0.8, True),
            ConfidenceObservation(0.7, False),
        ],
    )
    assert stats.wins == 1
    assert stats.losses == 1
    assert stats.no_trades == 2
    assert stats.errors == 1
    assert stats.current_equity_eur == 1000 + win.net_pnl_eur + loss.net_pnl_eur
    assert stats.max_drawdown_pct <= 0
    assert stats.confidence_brier_score is not None
    assert isinstance(stats.score_points, int)
