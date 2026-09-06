from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import uuid
from typing import Any, Iterable

from .schemas import DecisionEvent


LOCKED_DECISION_FIELDS = (
    "decision_id",
    "idempotency_key",
    "decision_at",
    "cutoff_at",
    "action",
    "symbol",
    "notional_eur",
    "confidence",
    "horizon_days",
    "stop_pct",
    "thesis",
    "counter_thesis",
    "prompt_version",
    "model",
    "sources_hash",
)


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def locked_decision_hash(event: DecisionEvent) -> str:
    payload = event.to_dict()
    locked = {key: payload[key] for key in LOCKED_DECISION_FIELDS}
    return stable_hash(locked)


def with_locked_hash(event: DecisionEvent) -> DecisionEvent:
    unsigned = replace(event, locked_payload_hash="")
    digest = locked_decision_hash(unsigned)
    return replace(event, locked_payload_hash=digest)


def verify_locked_hash(event: DecisionEvent) -> bool:
    return bool(event.locked_payload_hash) and event.locked_payload_hash == locked_decision_hash(event)


def make_decision_id(idempotency_key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"ai-trading-forward-lab:{idempotency_key}"))


def make_idempotency_key(session_date: str, protocol_version: str = "v1") -> str:
    if not session_date.strip() or not protocol_version.strip():
        raise ValueError("session_date and protocol_version are required")
    return f"decision:{protocol_version}:{session_date}"


def append_jsonl(path: str | Path, payload: dict[str, Any], *, unique_key: str | None = None) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = list(read_jsonl(target)) if target.exists() else []
    if unique_key is not None:
        candidate = payload.get(unique_key)
        if candidate is None:
            raise ValueError(f"payload missing unique key {unique_key}")
        if any(row.get(unique_key) == candidate for row in existing):
            raise ValueError(f"duplicate {unique_key}: {candidate}")
    line = canonical_json(payload) + "\n"
    with target.open("a", encoding="utf-8", newline="") as handle:
        handle.write(line)


def read_jsonl(path: str | Path) -> Iterable[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    with target.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at line {line_number}: {exc}") from exc
    return rows


def append_decision(path: str | Path, event: DecisionEvent) -> DecisionEvent:
    locked = event if event.locked_payload_hash else with_locked_hash(event)
    locked.validate()
    if not verify_locked_hash(locked):
        raise ValueError("locked payload hash mismatch")
    append_jsonl(path, locked.to_dict(), unique_key="decision_id")
    return locked
