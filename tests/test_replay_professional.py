from __future__ import annotations

import pytest

from engine.replay_professional import _simulate_entry_and_exit, _technical_summary, _validate_sources


def _rows(n: int, start: float = 100.0):
    rows=[]
    price=start
    for i in range(n):
        price += 0.5
        rows.append({
            "date": f"2025-{(i//28)%12+1:02d}-{(i%28)+1:02d}",
            "open": price-0.2,
            "high": price+1.0,
            "low": price-1.0,
            "close": price,
            "volume": 1000+i,
        })
    return rows


def test_technical_summary_uses_long_history():
    rows=_rows(260)
    summary=_technical_summary(rows, rows)
    assert summary["history_sessions_available"] == 260
    assert summary["sma"]["200"] is not None
    assert summary["returns_pct"]["252d"] is not None
    assert summary["relative_strength_vs_spy_20d_pct"] == pytest.approx(0.0)


def test_source_validation_rejects_future_news():
    decision={"sources":[{"url":"https://example.com/a","published_at":"2026-09-02T12:00:00Z","label":"A"}]}
    news=[{"url":"https://example.com/a"}]
    with pytest.raises(RuntimeError, match="post-cutoff"):
        _validate_sources(decision, news, "2026-09-01T20:05:00Z")


def test_source_validation_rejects_unknown_url():
    decision={"sources":[{"url":"https://example.com/missing","published_at":"2026-09-01T12:00:00Z","label":"A"}]}
    with pytest.raises(RuntimeError, match="outside supplied"):
        _validate_sources(decision, [{"url":"https://example.com/a"}], "2026-09-01T20:05:00Z")


def test_simulated_result_follows_selected_exit_day():
    rows=[
        {"date":"2026-09-01","open":100.0,"high":101.0,"low":99.0,"close":100.0,"volume":1},
        {"date":"2026-09-02","open":100.0,"high":103.0,"low":99.0,"close":102.0,"volume":1},
        {"date":"2026-09-03","open":102.0,"high":106.0,"low":101.0,"close":105.0,"volume":1},
    ]
    decision={"action":"BUY","notional_eur":100.0,"horizon_days":2}
    result=_simulate_entry_and_exit(decision, rows, cutoff_day="2026-09-01", exit_day="2026-09-03")
    assert result["entry_day"] == "2026-09-02"
    assert result["exit_day"] == "2026-09-03"
    assert result["net_pnl_eur"] > 0


def test_no_trade_never_changes_capital():
    result=_simulate_entry_and_exit({"action":"NO_TRADE"}, [], cutoff_day="2026-09-01", exit_day=None)
    assert result["net_pnl_eur"] == 0.0
