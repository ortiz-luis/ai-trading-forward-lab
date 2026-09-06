from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .portfolio import rebuild_portfolio_from_ledger
from .schemas import DecisionEvent, EvaluationEvent
from .ledger import read_jsonl
from .statistics import build_statistics

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"OPENAI_API_KEY", re.I),
    re.compile(r"ALPACA_API_(KEY|SECRET)", re.I),
]


def _load_decisions(path: Path) -> list[DecisionEvent]:
    return [DecisionEvent.from_dict(row) for row in read_jsonl(path)]


def _load_evaluations(path: Path) -> list[EvaluationEvent]:
    return [EvaluationEvent.from_dict(row) for row in read_jsonl(path)]


def _decision_card(event: DecisionEvent) -> dict[str, Any]:
    return {
        "decision_id": event.decision_id,
        "decision_at": event.decision_at,
        "action": event.action.value,
        "symbol": event.symbol,
        "notional_eur": event.notional_eur,
        "confidence": event.confidence,
        "horizon_days": event.horizon_days,
        "stop_pct": event.stop_pct,
        "thesis": event.thesis,
        "counter_thesis": event.counter_thesis,
    }


def build_public_dashboard(
    *,
    decisions_path: str | Path,
    evaluations_path: str | Path,
    health_path: str | Path,
    output_path: str | Path,
    starting_capital_eur: float = 1000.0,
) -> dict[str, Any]:
    decisions_path = Path(decisions_path)
    evaluations_path = Path(evaluations_path)
    health_path = Path(health_path)
    output_path = Path(output_path)

    decisions = _load_decisions(decisions_path) if decisions_path.exists() else []
    evaluations = _load_evaluations(evaluations_path) if evaluations_path.exists() else []
    evaluation_by_decision = {row.decision_id: row for row in evaluations}

    portfolio = rebuild_portfolio_from_ledger(
        decisions_path,
        starting_capital_eur=starting_capital_eur,
    ) if decisions_path.exists() else None

    no_trades = sum(d.action.value == "NO_TRADE" for d in decisions)
    stats = build_statistics(
        evaluations,
        starting_capital_eur=starting_capital_eur,
        no_trades=no_trades,
        errors=0,
    )

    equity = starting_capital_eur
    equity_series = [{"index": 0, "equity_eur": equity}]
    history: list[dict[str, Any]] = []
    for idx, decision in enumerate(decisions, start=1):
        evaluation = evaluation_by_decision.get(decision.decision_id)
        pnl = evaluation.net_pnl_eur if evaluation else None
        if pnl is not None:
            equity += pnl
        history.append({
            "decision_id": decision.decision_id,
            "decision_at": decision.decision_at,
            "action": decision.action.value,
            "symbol": decision.symbol,
            "notional_eur": decision.notional_eur,
            "confidence": decision.confidence,
            "net_pnl_eur": pnl,
            "result": "WIN" if pnl is not None and pnl > 0 else "LOSS" if pnl is not None and pnl < 0 else "FLAT" if pnl == 0 else "OPEN" if decision.action.value != "NO_TRADE" else "NO_TRADE",
        })
        equity_series.append({"index": idx, "equity_eur": equity})

    health = {}
    if health_path.exists():
        health = json.loads(health_path.read_text(encoding="utf-8"))

    payload = {
        "simulation_only": True,
        "starting_capital_eur": starting_capital_eur,
        "current_equity_eur": stats.current_equity_eur,
        "total_net_pnl_eur": stats.total_net_pnl_eur,
        "counts": {
            "decisions": len(decisions),
            "wins": stats.wins,
            "losses": stats.losses,
            "breakeven": stats.breakeven,
            "no_trades": stats.no_trades,
            "errors": stats.errors,
        },
        "latest_decision": _decision_card(decisions[-1]) if decisions else None,
        "open_positions": [] if portfolio is None else [
            {"symbol": symbol, "notional_eur": position.notional_eur}
            for symbol, position in sorted(portfolio.positions.items())
        ],
        "equity_series": equity_series,
        "history": history[-30:],
        "while_away": history[-7:],
        "health": {
            key: value for key, value in health.items()
            if key in {"last_decision_success_at", "last_evaluation_success_at", "last_error_at", "last_error_kind"}
        },
        "advanced": {
            "max_drawdown_pct": stats.max_drawdown_pct,
            "benchmark_return_pct_mean": stats.benchmark_return_pct_mean,
            "score_points": stats.score_points,
        },
    }

    text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    assert_public_safe(text)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
    return payload


def assert_public_safe(text: str) -> None:
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            raise ValueError(f"publishable artifact matched secret pattern: {pattern.pattern}")
