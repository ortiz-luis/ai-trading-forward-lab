from __future__ import annotations

from datetime import date, datetime
import json
from pathlib import Path
from typing import Any

from .public_data import assert_public_safe


class ReplayArtifactError(ValueError):
    pass


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_professional_replay_payload(payload: dict[str, Any]) -> None:
    if payload.get("version") != "professional-v2":
        raise ReplayArtifactError("unexpected replay version")
    if payload.get("forward_ledger_untouched") is not True:
        raise ReplayArtifactError("forward ledger isolation flag is not true")
    sessions = payload.get("sessions")
    if not isinstance(sessions, list):
        raise ReplayArtifactError("sessions must be a list")
    ids: set[str] = set()
    for session in sessions:
        replay_id = session.get("replay_id")
        if not isinstance(replay_id, str) or replay_id in ids:
            raise ReplayArtifactError("replay ids must be unique non-empty strings")
        ids.add(replay_id)
        cutoff_at = session.get("cutoff_at")
        cutoff_date = session.get("cutoff_date")
        if not isinstance(cutoff_at, str) or not isinstance(cutoff_date, str):
            raise ReplayArtifactError("cutoff fields are required")
        cutoff_dt = _dt(cutoff_at)
        cutoff_day = date.fromisoformat(cutoff_date)

        for evidence in session.get("evidence", []):
            published = evidence.get("published_at")
            if published and _dt(published) > cutoff_dt:
                raise ReplayArtifactError(f"post-cutoff evidence in {replay_id}")

        chart = session.get("chart") or {}
        for row in chart.get("candles_before_cutoff", []):
            if date.fromisoformat(row["date"]) > cutoff_day:
                raise ReplayArtifactError(f"future candle in pre-cutoff chart for {replay_id}")
        for row in chart.get("spy_before_cutoff", []):
            if date.fromisoformat(row["date"]) > cutoff_day:
                raise ReplayArtifactError(f"future SPY candle in pre-cutoff chart for {replay_id}")
        for row in chart.get("candles_after_cutoff", []):
            if date.fromisoformat(row["date"]) <= cutoff_day:
                raise ReplayArtifactError(f"non-future candle in reveal section for {replay_id}")
        for row in chart.get("spy_after_cutoff", []):
            if date.fromisoformat(row["date"]) <= cutoff_day:
                raise ReplayArtifactError(f"non-future SPY candle in reveal section for {replay_id}")

        lifecycle = session.get("lifecycle") or []
        for row in lifecycle:
            if date.fromisoformat(row["date"]) <= cutoff_day:
                raise ReplayArtifactError(f"lifecycle row is not post-entry for {replay_id}")

        decision = session.get("decision") or {}
        if decision.get("action") == "BUY":
            if decision.get("symbol") != chart.get("symbol"):
                raise ReplayArtifactError(f"BUY symbol/chart symbol mismatch for {replay_id}")
            result = session.get("result") or {}
            if result.get("available"):
                if not result.get("entry_day") or date.fromisoformat(result["entry_day"]) <= cutoff_day:
                    raise ReplayArtifactError(f"invalid entry day for {replay_id}")
                if not result.get("exit_day") or date.fromisoformat(result["exit_day"]) < date.fromisoformat(result["entry_day"]):
                    raise ReplayArtifactError(f"invalid exit day for {replay_id}")

    assert_public_safe(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def validate_professional_replay_file(path: str | Path = "data/replay_v2/index.json") -> None:
    raw = Path(path).read_text(encoding="utf-8")
    payload = json.loads(raw)
    validate_professional_replay_payload(payload)


def main() -> int:
    validate_professional_replay_file()
    print("professional_replay_artifact=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
