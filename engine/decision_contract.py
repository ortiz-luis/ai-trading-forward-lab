from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .protocol import PROTOCOL_V1
from .schemas import Action

PROMPT_VERSION = "trading-v1"

DECISION_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "action",
        "symbol",
        "notional_eur",
        "confidence",
        "horizon_days",
        "stop_pct",
        "thesis",
        "counter_thesis",
        "sources",
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
    model_identifier: str


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

        if self.action == Action.BUY:
            if self.symbol not in PROTOCOL_V1.tradable_universe:
                raise ValueError("BUY symbol outside protocol universe")
            if self.notional_eur <= 0:
                raise ValueError("BUY requires positive notional")
            if not PROTOCOL_V1.min_horizon_days <= self.horizon_days <= PROTOCOL_V1.max_horizon_days:
                raise ValueError("BUY horizon outside protocol bounds")
            if self.stop_pct is None or not PROTOCOL_V1.max_stop_pct <= self.stop_pct <= PROTOCOL_V1.min_stop_pct:
                raise ValueError("BUY stop outside protocol bounds")
        elif self.action in {Action.HOLD, Action.SELL}:
            if self.symbol not in PROTOCOL_V1.tradable_universe:
                raise ValueError("symbol outside protocol universe")
            if self.notional_eur != 0:
                raise ValueError("HOLD/SELL must use zero notional")
            if self.stop_pct is not None or self.horizon_days != 0:
                raise ValueError("HOLD/SELL use no new stop or horizon")
        elif self.action == Action.NO_TRADE:
            if self.symbol is not None or self.notional_eur != 0 or self.stop_pct is not None or self.horizon_days != 0:
                raise ValueError("NO_TRADE must not allocate or specify a position")


def build_prompt_input(input_data: DecisionInput) -> dict[str, Any]:
    if not input_data.cutoff_at:
        raise ValueError("cutoff_at is required")
    if not input_data.model_identifier.strip():
        raise ValueError("model_identifier is required")
    return {
        "cutoff_at": input_data.cutoff_at,
        "portfolio": input_data.portfolio,
        "protocol": input_data.protocol,
        "market": input_data.market,
        "evidence": input_data.evidence,
        "prompt_version": PROMPT_VERSION,
        "model_identifier": input_data.model_identifier,
    }
