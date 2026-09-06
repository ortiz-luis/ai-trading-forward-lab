from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import StrEnum
import hashlib
import json
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


class EvidenceKind(StrEnum):
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"


class EvidenceError(ValueError):
    pass


class PostCutoffEvidence(EvidenceError):
    pass


class StaleEvidence(EvidenceError):
    pass


class UndatedEvidence(EvidenceError):
    pass


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise EvidenceError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class EvidenceRecord:
    url: str
    source_name: str
    kind: EvidenceKind
    title: str
    published_at: str | None
    retrieved_at: str
    summary: str

    def validate(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise EvidenceError("evidence url must be absolute http(s)")
        if not self.source_name.strip():
            raise EvidenceError("source_name is required")
        if not self.title.strip():
            raise EvidenceError("title is required")
        if not self.summary.strip():
            raise EvidenceError("summary is required")
        if not isinstance(self.kind, EvidenceKind):
            raise EvidenceError("kind must be EvidenceKind")
        _utc(self.retrieved_at)
        if self.published_at is not None:
            _utc(self.published_at)

    def to_dict(self) -> dict[str, object]:
        self.validate()
        payload = asdict(self)
        payload["kind"] = self.kind.value
        return payload


@dataclass(frozen=True)
class EvidencePolicy:
    max_items: int = 12
    primary_max_age_hours: int = 24 * 7
    secondary_max_age_hours: int = 72
    require_published_at: bool = True

    def validate(self) -> None:
        if self.max_items < 1:
            raise EvidenceError("max_items must be >= 1")
        if self.primary_max_age_hours < 1 or self.secondary_max_age_hours < 1:
            raise EvidenceError("evidence age limits must be positive")


DEFAULT_EVIDENCE_POLICY = EvidencePolicy()


def evidence_age_hours(record: EvidenceRecord, *, cutoff_at: str) -> float:
    record.validate()
    cutoff = _utc(cutoff_at)
    if record.published_at is None:
        raise UndatedEvidence(f"published_at is required for {record.url}")
    published = _utc(record.published_at)
    if published > cutoff:
        raise PostCutoffEvidence(f"evidence published after cutoff: {record.url}")
    return (cutoff - published).total_seconds() / 3600.0


def validate_evidence_for_cutoff(
    record: EvidenceRecord,
    *,
    cutoff_at: str,
    policy: EvidencePolicy = DEFAULT_EVIDENCE_POLICY,
) -> EvidenceRecord:
    policy.validate()
    record.validate()
    cutoff = _utc(cutoff_at)
    retrieved = _utc(record.retrieved_at)

    if policy.require_published_at and record.published_at is None:
        raise UndatedEvidence(f"undated evidence rejected: {record.url}")

    published = _utc(record.published_at) if record.published_at is not None else None
    # Future information is the highest-priority failure class. Detect it before
    # checking publication/retrieval ordering so leakage is never hidden behind a
    # generic timestamp-consistency error.
    if published is not None and published > cutoff:
        raise PostCutoffEvidence(f"evidence published after cutoff: {record.url}")
    if retrieved > cutoff:
        raise PostCutoffEvidence(f"evidence retrieved after cutoff: {record.url}")
    if published is not None and retrieved < published:
        raise EvidenceError("retrieved_at cannot precede published_at")

    age = evidence_age_hours(record, cutoff_at=cutoff_at)
    max_age = policy.primary_max_age_hours if record.kind == EvidenceKind.PRIMARY else policy.secondary_max_age_hours
    if age > max_age:
        raise StaleEvidence(f"evidence too old for decision context: {record.url}")
    return record


def build_evidence_context(
    records: Iterable[EvidenceRecord],
    *,
    cutoff_at: str,
    policy: EvidencePolicy = DEFAULT_EVIDENCE_POLICY,
) -> tuple[EvidenceRecord, ...]:
    valid = [validate_evidence_for_cutoff(row, cutoff_at=cutoff_at, policy=policy) for row in records]
    valid.sort(
        key=lambda row: (
            0 if row.kind == EvidenceKind.PRIMARY else 1,
            -_utc(row.published_at or cutoff_at).timestamp(),
            row.url,
        )
    )
    return tuple(valid[: policy.max_items])


def manifest_payload(records: Iterable[EvidenceRecord], *, cutoff_at: str) -> dict[str, object]:
    rows = [row.to_dict() for row in records]
    canonical_rows = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        "cutoff_at": cutoff_at,
        "count": len(rows),
        "records": rows,
        "records_sha256": hashlib.sha256(canonical_rows.encode("utf-8")).hexdigest(),
    }


def write_evidence_manifest(path: str | Path, records: Iterable[EvidenceRecord], *, cutoff_at: str) -> dict[str, object]:
    payload = manifest_payload(records, cutoff_at=cutoff_at)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload
