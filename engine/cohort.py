from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any


class CohortStartBlocked(RuntimeError):
    pass


@dataclass(frozen=True)
class CohortFreeze:
    cohort_id: str
    status: str
    starting_capital_eur: float
    protocol_version: str
    prompt_version: str
    model: str
    market_provider: str
    evidence_policy: dict[str, Any]
    decision_schedule: str
    timezone: str
    frozen_components: dict[str, str]
    started_at: str | None = None
    observation_count: int = 0

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "CohortFreeze":
        return cls(**payload)

    def validate(self) -> None:
        if self.cohort_id != "forward-v1":
            raise ValueError("unexpected cohort_id")
        if self.status not in {"ARMED_NOT_STARTED", "STARTED"}:
            raise ValueError("invalid cohort status")
        if self.starting_capital_eur != 1000.0:
            raise ValueError("v1 starting capital is frozen at EUR 1000")
        if self.protocol_version != "v1" or self.prompt_version != "trading-v1":
            raise ValueError("v1 protocol/prompt versions are frozen")
        if not self.model or not self.market_provider:
            raise ValueError("model/provider are required")
        if self.observation_count < 0:
            raise ValueError("observation_count cannot be negative")
        if self.status == "ARMED_NOT_STARTED" and (self.started_at is not None or self.observation_count != 0):
            raise ValueError("armed cohort cannot contain observations")
        if self.status == "STARTED" and self.started_at is None:
            raise ValueError("started cohort requires started_at")
        required_components = {"prompt", "protocol", "evidence", "openai_provider", "market_provider", "evaluator"}
        if set(self.frozen_components) != required_components:
            raise ValueError("frozen component set mismatch")
        if any(not value for value in self.frozen_components.values()):
            raise ValueError("frozen component SHA cannot be empty")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_cohort(path: str | Path = "data/cohort_v1.json") -> CohortFreeze:
    cohort = CohortFreeze.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
    cohort.validate()
    return cohort


def validate_start_prerequisites(
    *,
    cohort_path: str | Path = "data/cohort_v1.json",
    runtime_context_path: str | Path = "data/runtime_context.json",
    decisions_path: str | Path = "data/decisions.jsonl",
    env: dict[str, str] | None = None,
) -> CohortFreeze:
    cohort = load_cohort(cohort_path)
    if cohort.status != "ARMED_NOT_STARTED":
        raise CohortStartBlocked("cohort is not in ARMED_NOT_STARTED state")
    if Path(decisions_path).exists() and Path(decisions_path).read_text(encoding="utf-8").strip():
        raise CohortStartBlocked("official cohort cannot start on top of existing decisions")
    if not Path(runtime_context_path).exists():
        raise CohortStartBlocked("sanitized runtime_context.json is required before observation #1")
    source = os.environ if env is None else env
    required = ("OPENAI_API_KEY", "ALPACA_API_KEY", "ALPACA_API_SECRET")
    missing = [name for name in required if not source.get(name)]
    if missing:
        raise CohortStartBlocked("required runtime secrets are unavailable: " + ", ".join(missing))
    return cohort


def start_cohort(
    *,
    cohort_path: str | Path = "data/cohort_v1.json",
    runtime_context_path: str | Path = "data/runtime_context.json",
    decisions_path: str | Path = "data/decisions.jsonl",
    env: dict[str, str] | None = None,
    started_at: str | None = None,
) -> CohortFreeze:
    cohort = validate_start_prerequisites(
        cohort_path=cohort_path,
        runtime_context_path=runtime_context_path,
        decisions_path=decisions_path,
        env=env,
    )
    started = replace(cohort, status="STARTED", started_at=started_at or utc_now_iso())
    started.validate()
    target = Path(cohort_path)
    target.write_text(json.dumps(asdict(started), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return started
