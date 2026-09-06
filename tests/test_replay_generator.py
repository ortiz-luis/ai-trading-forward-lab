from engine.replay_generator import _cutoff_at, _next_day_result


def test_cutoff_is_after_us_market_close_and_timezone_aware():
    cutoff = _cutoff_at("2026-09-03")
    assert cutoff.endswith("Z")
    assert "20:05:00" in cutoff


def test_next_day_buy_result_uses_only_next_session_prices():
    bars = {
        "SPY": [
            {"date": "2026-09-03", "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 1},
            {"date": "2026-09-04", "open": 100.0, "high": 103.0, "low": 99.0, "close": 102.0, "volume": 1},
        ],
        "AAPL": [
            {"date": "2026-09-03", "open": 200.0, "high": 201.0, "low": 198.0, "close": 200.0, "volume": 1},
            {"date": "2026-09-04", "open": 200.0, "high": 211.0, "low": 199.0, "close": 210.0, "volume": 1},
        ],
    }
    decision = {"action": "BUY", "symbol": "AAPL", "notional_eur": 100.0}
    result = _next_day_result(
        decision,
        replay_day="2026-09-03",
        next_day="2026-09-04",
        all_bars=bars,
    )
    assert result["available"] is True
    assert result["session_date"] == "2026-09-04"
    assert result["entry"] > 200.0
    assert result["close"] == 210.0
    assert result["net_pnl_eur"] > 0


def test_no_trade_keeps_capital_flat():
    bars = {
        "SPY": [
            {"date": "2026-09-04", "open": 100.0, "high": 103.0, "low": 99.0, "close": 102.0, "volume": 1},
        ],
    }
    result = _next_day_result(
        {"action": "NO_TRADE", "symbol": None, "notional_eur": 0.0},
        replay_day="2026-09-03",
        next_day="2026-09-04",
        all_bars=bars,
    )
    assert result["net_pnl_eur"] == 0.0
    assert result["benchmark_return_pct"] == 2.0
