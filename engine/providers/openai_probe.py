from __future__ import annotations

import json
from pathlib import Path

from ..decision_contract import DecisionInput
from .openai_decision import DecisionProviderError, OpenAIDecisionProvider


def main() -> int:
    prompt_path = Path(__file__).resolve().parents[2] / "prompts" / "trading_v1.md"
    instructions = prompt_path.read_text(encoding="utf-8")

    fixture = DecisionInput(
        cutoff_at="2026-09-06T14:00:00Z",
        portfolio={"cash_eur": 1000.0, "equity_eur": 1000.0, "positions": {}},
        protocol={"version": "v1", "simulation_only": True},
        market={"META": {"price": 100.0, "currency": "USD", "fixture": True}},
        evidence=[{
            "url": "https://example.com/synthetic-fixture",
            "published_at": "2026-09-06T12:00:00Z",
        }],
    )

    try:
        provider = OpenAIDecisionProvider()
        result = provider.decide(fixture, instructions=instructions)
    except DecisionProviderError as exc:
        print(json.dumps({"ok": False, "error_code": "AI_ERROR", "message": str(exc)}))
        return 2

    public = {
        "ok": result.ok,
        "model": result.model,
        "response_id": result.response_id,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.total_tokens,
        "repaired": result.repaired,
        "error_code": result.error_code,
        "error_message": result.error_message,
        "decision": None if result.decision is None else {
            "action": result.decision.action.value,
            "symbol": result.decision.symbol,
            "notional_eur": result.decision.notional_eur,
            "confidence": result.decision.confidence,
            "horizon_days": result.decision.horizon_days,
            "stop_pct": result.decision.stop_pct,
        },
    }
    print(json.dumps(public, sort_keys=True))
    return 0 if result.ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
