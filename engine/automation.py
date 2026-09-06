from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable

from .ledger import append_jsonl, make_idempotency_key, read_jsonl


@dataclass(frozen=True)
class HealthState:
    status: str
    updated_at: str
    last_decision_at: str | None = None
    last_evaluation_at: str | None = None
    last_error_kind: str | None = None
    last_error_message: str | None = None


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_health(path: str | Path, state: HealthState) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(state), sort_keys=True, indent=2) + "\n", encoding="utf-8")


def read_health(path: str | Path) -> HealthState | None:
    target = Path(path)
    if not target.exists():
        return None
    return HealthState(**json.loads(target.read_text(encoding="utf-8")))


def decision_already_exists(path: str | Path, *, session_date: str, protocol_version: str = "v1") -> bool:
    key = make_idempotency_key(session_date, protocol_version)
    return any(row.get("idempotency_key") == key for row in read_jsonl(path))


def record_system_error(
    path: str | Path,
    *,
    kind: str,
    message: str,
    occurred_at: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    timestamp = occurred_at or utc_now_iso()
    append_jsonl(
        path,
        {
            "event_type": "system",
            "system_event_id": f"{kind}:{timestamp}",
            "occurred_at": timestamp,
            "kind": kind,
            "message": message,
            "details": details or {},
        },
    )


def run_guarded_step(
    *,
    step_name: str,
    callback: Callable[[], Any],
    health_path: str | Path,
    system_events_path: str | Path,
    error_kind: str,
) -> Any | None:
    previous = read_health(health_path)
    try:
        result = callback()
    except Exception as exc:  # boundary: convert external/runtime failures to explicit state
        now = utc_now_iso()
        record_system_error(
            system_events_path,
            kind=error_kind,
            message=f"{step_name} failed: {type(exc).__name__}: {exc}",
            occurred_at=now,
        )
        write_health(
            health_path,
            HealthState(
                status="DEGRADED",
                updated_at=now,
                last_decision_at=previous.last_decision_at if previous else None,
                last_evaluation_at=previous.last_evaluation_at if previous else None,
                last_error_kind=error_kind,
                last_error_message=str(exc),
            ),
        )
        return None
    return result


def mark_decision_success(health_path: str | Path, *, at: str | None = None) -> None:
    now = at or utc_now_iso()
    previous = read_health(health_path)
    write_health(
        health_path,
        HealthState(
            status="HEALTHY",
            updated_at=now,
            last_decision_at=now,
            last_evaluation_at=previous.last_evaluation_at if previous else None,
        ),
    )


def mark_evaluation_success(health_path: str | Path, *, at: str | None = None) -> None:
    now = at or utc_now_iso()
    previous = read_health(health_path)
    write_health(
        health_path,
        HealthState(
            status="HEALTHY",
            updated_at=now,
            last_decision_at=previous.last_decision_at if previous else None,
            last_evaluation_at=now,
        ),
    )
