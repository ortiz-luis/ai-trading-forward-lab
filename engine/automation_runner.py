from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path

from .automation import (
    decision_already_exists,
    mark_decision_success,
    mark_evaluation_success,
    record_system_error,
    run_guarded_step,
)

DATA_DIR = Path("data")
DECISIONS = DATA_DIR / "decisions.jsonl"
SYSTEM_EVENTS = DATA_DIR / "system_events.jsonl"
HEALTH = DATA_DIR / "health.json"


def _session_date() -> str:
    explicit = os.getenv("AITFL_SESSION_DATE")
    if explicit:
        return explicit
    return datetime.utcnow().date().isoformat()


def run_decision_cycle() -> int:
    session_date = _session_date()
    if decision_already_exists(DECISIONS, session_date=session_date):
        return 0

    required = ["OPENAI_API_KEY", "ALPACA_API_KEY", "ALPACA_API_SECRET"]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        record_system_error(
            SYSTEM_EVENTS,
            kind="DATA_ERROR",
            message="decision cycle blocked because required runtime secrets are unavailable",
            details={"missing_secret_names": missing},
        )
        return 0

    # Full context acquisition is intentionally fail-closed until an evidence source
    # supplies a sanitized, timestamped context artifact. This runner establishes the
    # unattended control boundary without inventing evidence.
    context_path = DATA_DIR / "runtime_context.json"
    if not context_path.exists():
        record_system_error(
            SYSTEM_EVENTS,
            kind="DATA_ERROR",
            message="decision cycle blocked: sanitized runtime_context.json is absent",
        )
        return 0

    def _decision_boundary():
        from .providers.openai_provider import OpenAIDecisionProvider
        raise RuntimeError(
            "live decision orchestration requires the context-to-DecisionInput adapter; "
            "blocked rather than creating an unauditable decision"
        )

    result = run_guarded_step(
        step_name="decision",
        callback=_decision_boundary,
        health_path=HEALTH,
        system_events_path=SYSTEM_EVENTS,
        error_kind="AI_ERROR",
    )
    if result is None:
        return 0
    mark_decision_success(HEALTH)
    return 0


def run_evaluation_cycle() -> int:
    # Evaluation is safe to invoke periodically even when no position is ready.
    # The later data-build gate will supply price-window artifacts consumed here.
    evaluation_input = DATA_DIR / "evaluation_input.json"
    if not evaluation_input.exists():
        return 0

    def _evaluation_boundary():
        raise RuntimeError(
            "evaluation_input exists but production price-window adapter is not yet wired"
        )

    result = run_guarded_step(
        step_name="evaluation",
        callback=_evaluation_boundary,
        health_path=HEALTH,
        system_events_path=SYSTEM_EVENTS,
        error_kind="DATA_ERROR",
    )
    if result is None:
        return 0
    mark_evaluation_success(HEALTH)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["decision", "evaluate"])
    args = parser.parse_args()
    return run_decision_cycle() if args.mode == "decision" else run_evaluation_cycle()


if __name__ == "__main__":
    raise SystemExit(main())
