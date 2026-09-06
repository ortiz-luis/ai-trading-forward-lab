from engine.replay_professional_runner import _prior_levels


def test_current_candle_does_not_redefine_prior_resistance():
    rows = [
        {"low": 90.0, "high": 100.0},
        {"low": 92.0, "high": 101.0},
        {"low": 95.0, "high": 110.0},  # current breakout candle
    ]
    levels = _prior_levels(rows, sessions=60)
    assert levels["support"] == 90.0
    assert levels["resistance"] == 101.0
