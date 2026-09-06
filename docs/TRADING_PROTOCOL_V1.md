# Trading Protocol v1

Status: **FROZEN FOR COHORT v1 once the 35% gate is accepted.**

This protocol defines the allowed simulated trading behavior independently from any AI model. The AI may choose only among actions permitted here.

## 1. Objective

Test whether an AI using current public information can manage a small simulated portfolio prospectively over multi-day horizons without leverage.

## 2. Starting portfolio

- Starting simulated capital: **€1,000**.
- Base reporting currency: EUR.
- Tradable assets are US-listed equities priced in USD; currency conversion details will be handled deterministically by the evaluator/data layer when required.

## 3. Allowed universe

Initial v1 universe:

- AAPL
- MSFT
- NVDA
- AMZN
- META
- GOOGL
- AVGO
- AMD
- NFLX
- JPM
- V
- MA
- COST
- WMT
- UNH
- LLY
- XOM
- CVX
- SPY (benchmark only; not eligible for AI BUY in v1)

The universe is intentionally small, liquid, widely covered by primary and financial news sources, and available through Alpaca Market Data.

## 4. Direction and instrument restrictions

- Long-only.
- No short selling.
- No leverage or margin.
- No options.
- No futures.
- No CFDs.
- No crypto.
- No fractional synthetic derivatives.
- AI actions: `BUY`, `HOLD`, `SELL`, `NO_TRADE`.

## 5. Position limits

- Maximum simultaneous open positions: **3**.
- Maximum new position size: **15% of current simulated equity**.
- Maximum total invested exposure: **45% of current simulated equity**.
- Minimum BUY notional: **€50**, unless current equity is below €333, in which case minimum may be reduced to permit a position within the 15% cap.
- No pyramiding/add-on BUY in v1: one symbol may have at most one open position.

## 6. Sizing rule

The AI chooses notional size subject to hard limits.

Suggested confidence bands for interpretation, not mandatory allocation targets:

- confidence < 0.60 → normally `NO_TRADE`;
- 0.60–0.69 → up to 5% equity;
- 0.70–0.79 → up to 10% equity;
- >= 0.80 → up to 15% equity.

Deterministic guards always override the AI if requested notional violates the hard portfolio limits.

## 7. Entry semantics

For a new BUY decision:

1. The AI decision is locked first with its real decision timestamp.
2. The theoretical entry price is the first eligible market observation **after** the locked decision timestamp.
3. The system must never use a better earlier price or retrospectively select a favorable candle.
4. If no eligible price is available within the execution window, the decision becomes an explicit execution/data failure rather than a fabricated fill.

The exact price-source granularity and slippage model are implemented at the deterministic evaluator gate; the semantic rule above is frozen here.

## 8. Stop-loss rule

- Every BUY must specify a stop between **-1.0% and -5.0%** relative to theoretical entry.
- Default/reference stop: **-2.0%**.
- The stop is a risk rule, not a promise of exact fill; simulated slippage will be accounted for later.
- A stop cannot be widened after the position is opened during cohort v1.

## 9. Horizon rule

- Minimum intended holding horizon: **2 trading days**.
- Maximum horizon: **10 trading days**.
- Default/reference horizon: **5 trading days**.
- The AI may explicitly SELL earlier based on new evidence.
- If no earlier SELL/stop occurs, the evaluator closes at horizon expiry using the frozen deterministic exit rule.

## 10. HOLD rule

`HOLD` is valid only for an already-open symbol and must allocate zero new notional. It preserves the current stop and horizon unless a later protocol version explicitly permits amendments.

## 11. SELL rule

`SELL` may only close an existing position. v1 uses full-position exits only; partial exits are not allowed.

## 12. NO_TRADE rule

`NO_TRADE` is a first-class successful system outcome. It must be chosen when any of the following is true:

- no candidate has sufficient evidence/conviction;
- requested trade would violate portfolio limits;
- relevant market data are missing, stale or not eligible;
- evidence is contradictory or materially uncertain;
- the model cannot establish a thesis stronger than its counter-thesis;
- market conditions fall outside the frozen protocol;
- fewer than 2 trading days remain before a known protocol constraint that makes the chosen horizon invalid.

The system must never transform API/data/model errors into `NO_TRADE`; those remain explicit errors.

## 13. Evidence standard

The AI may use public information available at or before the cutoff timestamp. Primary sources are preferred where practical:

- company investor-relations releases;
- SEC/regulatory filings;
- official corporate announcements;
- recognized financial-news sources for context.

Information published after cutoff is prohibited for the decision being scored.

## 14. Benchmark

Primary benchmark: **SPY**.

Each completed trade is compared with SPY over the same theoretical entry and exit timestamps. Portfolio-level benchmark reporting will also compare cumulative strategy equity against SPY from cohort start.

## 15. Decision frequency

- At most **one scheduled AI decision cycle per US trading day** in cohort v1.
- A decision cycle may result in `BUY`, `HOLD`, `SELL`, or `NO_TRADE`.
- The manual trigger, when eventually implemented, must be clearly labeled separately and must not silently create duplicate same-session scheduled observations.

## 16. Market timing

The decision scheduler may run once per US trading day during a defined market-open window. Exact scheduler clock time is intentionally deferred to the automation gate, but actual execution timestamp must always be recorded and never backdated.

## 17. Costs and slippage

v1 will not assume zero-friction fills. Exact simulated transaction-cost/slippage parameters are implemented in the deterministic evaluator gate and frozen before cohort start.

## 18. Protocol immutability

Before observation #1, this protocol and its machine-readable configuration are tagged as cohort v1. Any later change creates a new protocol/cohort version; historical v1 decisions are never rescored under rewritten rules.

## 19. Safety boundary

This protocol governs simulated trading only. There is no automatic path from v1 decisions to real-money execution.
