from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from zoneinfo import ZoneInfo

PARIS_TZ = ZoneInfo("Europe/Paris")


class Action(StrEnum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    NO_TRADE = "NO_TRADE"


class SystemEventKind(StrEnum):
    INFO = "INFO"
    DATA_ERROR = "DATA_ERROR"
    AI_ERROR = "AI_ERROR"
    DEPLOY_ERROR = "DEPLOY_ERROR"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def normalize_utc_iso(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def paris_display(value: str) -> str:
    parsed = datetime.fromisoformat(normalize_utc_iso(value).replace("Z", "+00:00"))
    return parsed.astimezone(PARIS_TZ).isoformat(timespec="seconds")


def _require_nonempty(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


@dataclass(frozen=True)
class DecisionEvent:
    decision_id: str
    idempotency_key: str
    decision_at: str
    cutoff_at: str
    action: Action
    symbol: str | None
    notional_eur: float
    confidence: float
    horizon_days: int
    stop_pct: float | None
    thesis: str
    counter_thesis: str
    prompt_version: str
    model: str
    sources_hash: str
    locked_payload_hash: str = ""
    event_type: str = field(default="decision", init=False)

    def validate(self) -> None:
        for name in ("decision_id", "idempotency_key", "prompt_version", "model", "sources_hash"):
            _require_nonempty(name, getattr(self, name))
        normalize_utc_iso(self.decision_at)
        normalize_utc_iso(self.cutoff_at)
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be in [0, 1]")
        if self.notional_eur < 0:
            raise ValueError("notional_eur must be >= 0")
        if self.horizon_days < 0:
            raise ValueError("horizon_days must be >= 0")
        if self.action in {Action.BUY, Action.HOLD, Action.SELL} and not self.symbol:
            raise ValueError(f"symbol is required for {self.action}")
        if self.action == Action.NO_TRADE and self.notional_eur != 0:
            raise ValueError("NO_TRADE must use notional_eur=0")
        if self.symbol is not None and (not self.symbol.isascii() or self.symbol.upper() != self.symbol):
            raise ValueError("symbol must be uppercase ASCII")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        payload["action"] = self.action.value
        return payload


@dataclass(frozen=True)
class EvaluationEvent:
    evaluation_id: str
    decision_id: str
    evaluated_at: str
    exit_reason: str
    exit_price: float
    gross_pnl_eur: float
    costs_eur: float
    net_pnl_eur: float
    benchmark_return_pct: float
    event_type: str = field(default="evaluation", init=False)

    def validate(self) -> None:
        for name in ("evaluation_id", "decision_id", "exit_reason"):
            _require_nonempty(name, getattr(self, name))
        normalize_utc_iso(self.evaluated_at)
        if self.exit_price < 0:
            raise ValueError("exit_price must be >= 0")
        if self.costs_eur < 0:
            raise ValueError("costs_eur must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return asdict(self)


@dataclass(frozen=True)
class SystemEvent:
    system_event_id: str
    occurred_at: str
    kind: SystemEventKind
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    event_type: str = field(default="system", init=False)

    def validate(self) -> None:
        _require_nonempty("system_event_id", self.system_event_id)
        _require_nonempty("message", self.message)
        normalize_utc_iso(self.occurred_at)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload = asdict(self)
        payload["kind"] = self.kind.value
        return payload
