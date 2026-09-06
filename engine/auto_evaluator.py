from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from .automation import mark_evaluation_success, record_system_error
from .evaluator import EvaluationRules, PricePoint, evaluate_long_decision, to_evaluation_event
from .ledger import append_jsonl, read_jsonl, stable_hash
from .providers.alpaca import AlpacaMarketDataProvider
from .providers.market import MarketCandle, MarketDataProvider
from .schemas import Action, DecisionEvent, EvaluationEvent

NY = ZoneInfo("America/New_York")


def _dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(timezone.utc)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _price_points_after(candles: tuple[MarketCandle, ...], after: str) -> list[PricePoint]:
    cutoff = _dt(after)
    return [
        PricePoint(observed_at=row.end_at, price=row.close)
        for row in candles
        if _dt(row.end_at) > cutoff
    ]


def _trading_date(point: PricePoint):
    return _dt(point.observed_at).astimezone(NY).date()


def _first_sell_after(decisions: list[DecisionEvent], buy: DecisionEvent) -> DecisionEvent | None:
    candidates = [
        row for row in decisions
        if row.action == Action.SELL
        and row.symbol == buy.symbol
        and _dt(row.decision_at) > _dt(buy.decision_at)
    ]
    return min(candidates, key=lambda row: _dt(row.decision_at)) if candidates else None


def _aligned_benchmark(asset_points: list[PricePoint], benchmark_candles: tuple[MarketCandle, ...]) -> list[PricePoint]:
    benchmark = {
        row.end_at: PricePoint(observed_at=row.end_at, price=row.close)
        for row in benchmark_candles
    }
    missing = [row.observed_at for row in asset_points if row.observed_at not in benchmark]
    if missing:
        raise ValueError(f"benchmark missing {len(missing)} aligned timestamps")
    return [benchmark[row.observed_at] for row in asset_points]


def _ready_window(
    decision: DecisionEvent,
    asset_points: list[PricePoint],
    *,
    rules: EvaluationRules,
    explicit_sell: DecisionEvent | None,
) -> tuple[list[PricePoint], int | None] | None:
    if len(asset_points) < 2:
        return None

    if explicit_sell is not None:
        sell_at = _dt(explicit_sell.decision_at)
        for index, point in enumerate(asset_points[1:], start=1):
            if _dt(point.observed_at) >= sell_at:
                return asset_points[: index + 1], index

    entry = asset_points[0].price * (1 + rules.slippage_bps / 10000.0)
    stop = entry * (1 + (decision.stop_pct or 0.0))
    for index, point in enumerate(asset_points[1:], start=1):
        if decision.stop_pct is not None and point.price <= stop:
            return asset_points[: index + 1], None

    dates: list[object] = []
    for point in asset_points:
        day = _trading_date(point)
        if not dates or day != dates[-1]:
            dates.append(day)
        if len(dates) >= decision.horizon_days:
            horizon_day = dates[decision.horizon_days - 1]
            last_index = max(
                index for index, row in enumerate(asset_points)
                if _trading_date(row) == horizon_day
            )
            if last_index >= 1:
                return asset_points[: last_index + 1], None
    return None


def run_unattended_evaluations(
    *,
    provider: MarketDataProvider,
    decisions_path: str | Path = "data/decisions.jsonl",
    evaluations_path: str | Path = "data/evaluations.jsonl",
    system_events_path: str | Path = "data/system_events.jsonl",
    health_path: str | Path = "data/health.json",
    benchmark_symbol: str = "SPY",
    history_limit: int = 10000,
    rules: EvaluationRules | None = None,
) -> int:
    active_rules = rules or EvaluationRules()
    decisions = [DecisionEvent.from_dict(row) for row in read_jsonl(decisions_path)]
    evaluations = [EvaluationEvent.from_dict(row) for row in read_jsonl(evaluations_path)]
    evaluated_ids = {row.decision_id for row in evaluations}
    pending = [row for row in decisions if row.action == Action.BUY and row.decision_id not in evaluated_ids]
    if not pending:
        return 0

    benchmark_candles = tuple(provider.get_candles(benchmark_symbol, limit=history_limit))
    created = 0
    for decision in pending:
        try:
            assert decision.symbol is not None
            asset_candles = tuple(provider.get_candles(decision.symbol, limit=history_limit))
            points = _price_points_after(asset_candles, decision.decision_at)
            ready = _ready_window(
                decision,
                points,
                rules=active_rules,
                explicit_sell=_first_sell_after(decisions, decision),
            )
            if ready is None:
                continue
            asset_window, explicit_sell_index = ready
            benchmark_window = _aligned_benchmark(asset_window, benchmark_candles)
            result = evaluate_long_decision(
                decision,
                asset_prices=asset_window,
                benchmark_prices=benchmark_window,
                rules=active_rules,
                explicit_sell_index=explicit_sell_index,
            )
            now = _now_iso()
            evaluation_id = stable_hash({
                "decision_id": decision.decision_id,
                "exit_reason": result.exit_reason,
                "exit_price": result.exit_price,
            })[:32]
            event = to_evaluation_event(
                result,
                evaluation_id=evaluation_id,
                decision_id=decision.decision_id,
                evaluated_at=now,
            )
            append_jsonl(evaluations_path, event.to_dict(), unique_key="evaluation_id")
            created += 1
        except Exception as exc:
            record_system_error(
                system_events_path,
                kind="DATA_ERROR",
                message=f"unattended evaluation failed closed for {decision.decision_id}: {type(exc).__name__}: {exc}",
            )
    if created:
        mark_evaluation_success(health_path, at=_now_iso())
    return created


def main() -> int:
    provider = AlpacaMarketDataProvider()
    created = run_unattended_evaluations(provider=provider)
    print(f"evaluations_created={created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
