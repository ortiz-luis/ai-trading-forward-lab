from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .automation import (
    decision_already_exists,
    mark_decision_success,
    mark_evaluation_success,
    record_system_error,
)
from .cohort import load_cohort, record_observation
from .decision_contract import DecisionInput
from .evaluator import EvaluationRules, PricePoint, evaluate_long_decision, to_evaluation_event
from .ledger import append_decision, append_jsonl, make_decision_id, make_idempotency_key, stable_hash
from .schemas import DecisionEvent

DATA_DIR = Path("data")
DECISIONS = DATA_DIR / "decisions.jsonl"
EVALUATIONS = DATA_DIR / "evaluations.jsonl"
SYSTEM_EVENTS = DATA_DIR / "system_events.jsonl"
HEALTH = DATA_DIR / "health.json"
COHORT = DATA_DIR / "cohort_v1.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _session_date() -> str:
    explicit = os.getenv("AITFL_SESSION_DATE")
    if explicit:
        return explicit
    return datetime.now(timezone.utc).date().isoformat()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def run_decision_cycle() -> int:
    session_date = _session_date()
    key = make_idempotency_key(session_date, "v1")
    if decision_already_exists(DECISIONS, session_date=session_date):
        return 0

    try:
        cohort = load_cohort(COHORT)
    except Exception as exc:
        record_system_error(
            SYSTEM_EVENTS,
            kind="DATA_ERROR",
            message=f"decision cycle blocked: invalid/missing cohort freeze: {type(exc).__name__}: {exc}",
        )
        return 0
    if cohort.status != "STARTED":
        # ARMED_NOT_STARTED is a normal safe state, not an error. The authenticated
        # start-cohort workflow performs the one-way start transition.
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

    context_path = DATA_DIR / "runtime_context.json"
    if not context_path.exists():
        record_system_error(
            SYSTEM_EVENTS,
            kind="DATA_ERROR",
            message="decision cycle blocked: sanitized runtime_context.json is absent",
        )
        return 0

    try:
        raw = _load_json(context_path)
        input_data = DecisionInput(
            cutoff_at=raw["cutoff_at"],
            portfolio=raw["portfolio"],
            protocol=raw["protocol"],
            market=raw["market"],
            evidence=raw["evidence"],
            model_identifier=cohort.model,
        )
        instructions = Path("prompts/trading_v1.md").read_text(encoding="utf-8")

        from .providers.openai_decision import OpenAIDecisionProvider

        provider = OpenAIDecisionProvider(model=cohort.model)
        result = provider.decide(input_data, instructions=instructions)
        if not result.ok or result.decision is None:
            record_system_error(
                SYSTEM_EVENTS,
                kind="AI_ERROR",
                message=result.error_message or "OpenAI returned no valid decision",
                details={"model": result.model, "repaired": result.repaired},
            )
            return 0

        out = result.decision
        now = utc_now_iso()
        event = DecisionEvent(
            decision_id=make_decision_id(key),
            idempotency_key=key,
            decision_at=now,
            cutoff_at=input_data.cutoff_at,
            action=out.action,
            symbol=out.symbol,
            notional_eur=out.notional_eur,
            confidence=out.confidence,
            horizon_days=out.horizon_days,
            stop_pct=out.stop_pct,
            thesis=out.thesis,
            counter_thesis=out.counter_thesis,
            prompt_version=cohort.prompt_version,
            model=result.model,
            sources_hash=stable_hash({"sources": list(out.sources)}),
        )
        append_decision(DECISIONS, event)
        record_observation(COHORT)
        mark_decision_success(HEALTH, at=now)
        return 0
    except Exception as exc:
        record_system_error(
            SYSTEM_EVENTS,
            kind="AI_ERROR",
            message=f"decision cycle failed closed: {type(exc).__name__}: {exc}",
        )
        return 0


def run_evaluation_cycle() -> int:
    input_path = DATA_DIR / "evaluation_input.json"
    if not input_path.exists():
        return 0

    try:
        raw = _load_json(input_path)
        decision = DecisionEvent.from_dict(raw["decision"])
        asset_prices = tuple(PricePoint(**row) for row in raw["asset_prices"])
        benchmark_prices = tuple(PricePoint(**row) for row in raw["benchmark_prices"])
        rules = EvaluationRules(**raw.get("rules", {}))
        result = evaluate_long_decision(
            decision,
            asset_prices=asset_prices,
            benchmark_prices=benchmark_prices,
            rules=rules,
            explicit_sell_index=raw.get("explicit_sell_index"),
        )
        now = utc_now_iso()
        evaluation_id = stable_hash(
            {
                "decision_id": decision.decision_id,
                "exit_price": result.exit_price,
                "exit_reason": result.exit_reason,
            }
        )[:32]
        event = to_evaluation_event(
            result,
            evaluation_id=evaluation_id,
            decision_id=decision.decision_id,
            evaluated_at=now,
        )
        existing = []
        if EVALUATIONS.exists():
            existing = [json.loads(line) for line in EVALUATIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not any(row.get("evaluation_id") == evaluation_id for row in existing):
            append_jsonl(EVALUATIONS, event.to_dict(), unique_key="evaluation_id")
        mark_evaluation_success(HEALTH, at=now)
        return 0
    except Exception as exc:
        record_system_error(
            SYSTEM_EVENTS,
            kind="DATA_ERROR",
            message=f"evaluation cycle failed closed: {type(exc).__name__}: {exc}",
        )
        return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["decision", "evaluate"])
    args = parser.parse_args()
    return run_decision_cycle() if args.mode == "decision" else run_evaluation_cycle()


if __name__ == "__main__":
    raise SystemExit(main())
