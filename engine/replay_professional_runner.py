from __future__ import annotations

from typing import Any

from . import replay_professional as rp


_original_technical_summary = rp._technical_summary


def _prior_levels(rows: list[dict[str, Any]], sessions: int = 60) -> dict[str, float | None]:
    if len(rows) <= 1:
        return {"support": None, "resistance": None}
    prior = rows[-(sessions + 1):-1]
    if not prior:
        prior = rows[:-1]
    if not prior:
        return {"support": None, "resistance": None}
    return {
        "support": min(row["low"] for row in prior),
        "resistance": max(row["high"] for row in prior),
    }


def _enhanced_technical_summary(rows: list[dict[str, Any]], spy_rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = _original_technical_summary(rows, spy_rows)
    prior = _prior_levels(rows)
    price = rows[-1]["close"]
    resistance = prior["resistance"]
    support = prior["support"]
    summary["support_60d"] = support
    summary["resistance_60d"] = resistance
    summary["breakout_above_prior_60d_resistance_pct"] = (
        None if resistance is None else ((price / resistance) - 1.0) * 100.0
    )
    summary["distance_above_prior_60d_support_pct"] = (
        None if support is None else ((price / support) - 1.0) * 100.0
    )
    return summary


def main() -> int:
    # The core v2 module deliberately remains importable/testable in isolation.
    # Runtime generation patches level semantics so the current candle is never
    # allowed to redefine the resistance level being tested.
    rp._levels = _prior_levels
    rp._technical_summary = _enhanced_technical_summary
    payload = rp.generate_professional_replays()
    print(f"generated_professional_replays={payload['replay_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
