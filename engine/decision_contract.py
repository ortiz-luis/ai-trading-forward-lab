from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schemas import Action, DecisionEvent
from .protocol import PROTOCOL_V1

PROMPT_VERSION = "trading-v1"

DECISION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "action", "symbol", "notional_eur", "confidence", "horizon_days",
        "stop_pct", "thesis", "counter_thesis", "sources",
    ],
    "properties": {
        "action": {"type": "string", "enum": [a.value for a in Action]},
        "symbol": {"type": ["string", "null"]},
        "notional_eur": {"type": "number", "minimum": 0},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "horizon_days": {"type": "integer", "minimum": 0},
        "stop_pct": {"type": ["number", "null"]},
        "thesis": {"type": "string", "minLength": 1},
        "counter_thesis": {"type": "string", "minLength": 1},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["url", "published_at"],
                "properties": {
                    "url": {"type": "string", "minLength": 1},
                    "published_at": {"type": ["string", "null"]},
                },
            },
        },
    },
}


@dataclass(frozen=True)
class DecisionInput:
    cutoff_at: str
    portfolio: dict[str, Any]
    protocol: dict[str, Any]
    market: dict[str, Any]
    evidence: list[dict[str, Any]]
    model_identifier: str | None = None


@dataclass(frozen=True)
class DecisionOutput:
    action: Action
    symbol: str | None
    notional_eur: float
    confidence: float
    horizon_days: int
    stop_pct: float | None
    thesis: str
    counter_thesis: str
    sources: tuple[dict[str, Any], ...]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DecisionOutput":
        required = set(DECISION_JSON_SCHEMA["required"])
        if set(payload) != required:
            missing = required - set(payload)
            extra = set(payload) - required
            raise ValueError(f"decision keys mismatch: missing={sorted(missing)} extra={sorted(extra)}")
        out = cls(
            action=Action(payload["action"]),
            symbol=payload["symbol"],
            notional_eur=float(payload["notional_eur"]),
            confidence=float(payload["confidence"]),
            horizon_days=int(payload["horizon_days"]),
            stop_pct=None if payload["stop_pct"] is None else float(payload["stop_pct"]),
            thesis=str(payload["thesis"]),
            counter_thesis=str(payload["counter_thesis"]),
            sources=tuple(payload["sources"]),
        )
        out.validate()
        return out

    def validate(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be in [0,1]")
        if not self.thesis.strip() or not self.counter_thesis.strip():
            raise ValueError("thesis and counter_thesis are required")
        for source in self.sources:
            if set(source) != {"url", "published_at"}:
                raise ValueError("source must contain only url and published_at")
            if not isinstance(source["url"], str) or not source["url"].strip():
                raise ValueError("source url is required")

        event = DecisionEvent(
            decision_id="contract-validation",
            idempotency_key="contract-validation",
            decision_at="2026-01-01T00:00:00Z",
            cutoff_at="2026-01-01T00:00:00Z",
            action=self.action,
            symbol=self.symbol,
            notional_eur=self.notional_eur,
            confidence=self.confidence,
            horizon_days=self.horizon_days,
            stop_pct=self.stop_pct,
            thesis=self.thesis,
            counter_thesis=self.counter_thesis,
            prompt_version=PROMPT_VERSION,
            model="contract-validation",
            sources_hash="contract-validation",
        )
        PROTOCOL_V1.validate_decision(event, current_equity_eur=PROTOCOL_V1.starting_capital_eur)


def build_prompt_input(input_data: DecisionInput) -> dict[str, Any]:
    if not input_data.cutoff_at:
        raise ValueError("cutoff_at is required")
    return {
        "cutoff_at": input_data.cutoff_at,
        "portfolio": input_data.portfolio,
        "protocol": input_data.protocol,
        "market": input_data.market,
        "evidence": input_data.evidence,
        "prompt_version": PROMPT_VERSION,
        "model_identifier": input_data.model_identifier,
    }
