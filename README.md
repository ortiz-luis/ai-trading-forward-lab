# AI Trading Forward Lab

GitHub-first, forward-only experiment for observing how an AI manages a **simulated** portfolio over time.

> **Current progress: 25% / 100%**  
> **Current gate: STOP — waiting for explicit `sigue` before starting 30%.**

## Product goal

Build a low-friction hobby project that keeps running while the user is away: scheduled market context → fixed/versioned OpenAI decision → timestamped locked event → deterministic simulated accounting → simple public dashboard answering **“we started with €1,000; how much would we have now?”**

## Non-negotiable rules

- Phase 1: **no real money** and no live-broker credentials.
- Forward-only; no retroactive rewriting.
- AI decides; deterministic code calculates accounting/P&L.
- `NO_TRADE` is valid.
- Keys never appear in browser, repository data, Pages artifacts or logs.
- GitHub Pages = public UI; GitHub Actions = scheduled execution.
- Unattended AI uses OpenAI API, not browser automation of chatgpt.com.
- Each cohort freezes prompt, universe, sizing, timing and evaluation rules before observation #1.
- Work advances in exact **5% gates** and stops until the user says `sigue`.

## Target architecture

```text
GitHub Pages
     ↑ generated public data
GitHub Actions scheduler / manual dispatch
     ↓
Python engine
  ├─ Market data adapter
  ├─ Context builder
  ├─ OpenAI Responses API
  ├─ Schema validator
  ├─ Portfolio rules
  ├─ Append-only immutable ledger
  └─ Deterministic evaluator
     ↓
Git-versioned state → Pages rebuild
```

# Master implementation plan — 0% → 100%

A block is complete only when its acceptance criteria pass.

## 0% → 5% — Project control plane and architecture freeze ✅
- [x] Public repository and README master board.
- [x] Pages + Actions + Python + OpenAI API + market adapter + ledger architecture.
- [x] Simulation-only boundary and 5% stop/go cadence.
- [x] Architecture baseline and initial skeleton.

## 5% → 10% — Executable Python skeleton ✅
- [x] `pyproject.toml`, Python 3.11+, importable `engine`.
- [x] Offline `decide`, `evaluate`, `rebuild` interfaces.
- [x] Deterministic config, smoke tests and WSL/CI command.

## 10% → 15% — Event schemas and immutable ledger ✅
- [x] Strict decision/evaluation/system schemas.
- [x] UTC canonical storage + Europe/Paris display conversion.
- [x] Append-only canonical JSONL ledger.
- [x] Stable IDs/idempotency and SHA-256 locked payload hash.
- [x] Mutation/duplicate/round-trip tests.

## 15% → 20% — Portfolio accounting engine ✅
- [x] Starting simulated capital (€1,000 default/configurable).
- [x] Cash, equity, positions, realized/unrealized P&L fields.
- [x] BUY/HOLD/SELL/NO_TRADE transitions.
- [x] No leverage, non-negative cash and hard exposure limits.
- [x] Rebuild portfolio from immutable decision ledger.
- [x] Accounting invariant tests.

## 20% → 25% — Market-data provider abstraction ✅
- [x] Stable `MarketDataProvider` protocol.
- [x] Deterministic fixture provider for offline tests.
- [x] Selected **Alpaca Market Data API** as first real external adapter while keeping provider independence.
- [x] Normalized quote and candle timestamp models.
- [x] Sanitized audit-snapshot writer.
- [x] Explicit `MissingMarketData`, `StaleMarketData` and `MarketClosed` failure states.
- [x] Tradeability guard rejects stale or closed-market quotes.
- [x] Tests cover deterministic fixtures, missing/stale/closed/fresh data and candle validation.
- [x] Provider decision documented in `docs/MARKET_DATA_PROVIDER.md`.

**Acceptance:** fixture inputs produce deterministic normalized observations; missing/stale/closed-market data fails closed and cannot be treated as a tradeable quote. No external network/API call is introduced in this gate.

## 25% → 30% — Real market-data adapter
- [ ] Implement Alpaca adapter using environment/GitHub Secret credentials.
- [ ] Retrieve latest quotes/bars for a small allowed US-equity universe.
- [ ] Normalize provider timestamps, symbols and currencies into v1 models.
- [ ] Add timeout, bounded retry and explicit rate-limit handling.
- [ ] Add provider health state.
- [ ] Persist only sanitized observations; never credentials/headers.

**Acceptance:** manual network run yields a sanitized timestamped snapshot or an explicit clean failure.

## 30% → 35% — Trading protocol v1
- [ ] Freeze universe, long-only/no-leverage constraints and position limits.
- [ ] Freeze sizing/exposure, horizon/stop, entry/exit and benchmark rules.
- [ ] Define `NO_TRADE` conditions.

## 35% → 40% — OpenAI decision contract
- [ ] `prompts/trading_v1.md` + strict structured-output schema.
- [ ] Portfolio/cutoff/context input; thesis/counter-thesis/confidence/sources output.
- [ ] Prohibit post-cutoff information; first-class `NO_TRADE`.
- [ ] Prompt/model versions and fixtures.

## 40% → 45% — OpenAI API integration
- [ ] Official SDK behind `DecisionProvider`.
- [ ] Key only from environment/GitHub Secret.
- [ ] Timeout/bounded retry, one controlled repair, explicit `AI_ERROR`.
- [ ] Cost metadata where available; failure never becomes `NO_TRADE`.

## 45% → 50% — Context and evidence pipeline
- [ ] Evidence object with URL/source/publication/retrieval times.
- [ ] Prioritize primary sources; bounded recent-news/search context.
- [ ] Prevent stale evidence appearing current; persist evidence manifest.

## 50% → 55% — Deterministic evaluator
- [ ] Entry, stop, expiry and SELL rules.
- [ ] Configurable costs/slippage; gross/net P&L and benchmark.
- [ ] Evaluation event never alters decision event.

## 55% → 60% — Scoring and statistics
- [ ] Human-readable points; wins/losses/no-trades/errors separately.
- [ ] Equity, benchmark, drawdown and confidence calibration.
- [ ] Points never substitute monetary P&L.

## 60% → 65% — GitHub Actions automation core
- [ ] Daily schedule + `workflow_dispatch`.
- [ ] Timezone-aware timestamp, concurrency guard and idempotency.
- [ ] Controlled decision/validation/persistence/tests pipeline.

## 65% → 70% — Evaluation automation and resilience
- [ ] Periodic unattended evaluator and bounded retries.
- [ ] `DATA_ERROR`, `AI_ERROR`, `DEPLOY_ERROR`, `health.json`.
- [ ] Preserve prior site on failed build; synthetic multi-day test.

## 70% → 75% — Public-data build layer
- [ ] Sanitized dashboard JSON and no secret serialization.
- [ ] “Mientras no estuviste”, current portfolio, equity series and latest cards.
- [ ] Secret-pattern scan.

## 75% → 80% — Beginner-first GitHub Pages UI
- [ ] Responsive home page.
- [ ] Hero: starting money → current money → gain/loss.
- [ ] Simple latest decision, positions and green/red/neutral history.
- [ ] “Mientras no estuviste” + one cumulative equity chart.

## 80% → 85% — Pages deployment and manual interaction
- [ ] Official Pages deployment and correct base path.
- [ ] Authorized manual “request a decision now”.
- [ ] Health/update status, mobile/desktop and HTTPS validation.

## 85% → 90% — Optional Alpaca Paper shadow execution
- [ ] Paper-only broker adapter and credentials.
- [ ] Mirror eligible simulated orders and reconcile fills.
- [ ] Never overwrite internal ledger; hard-block live endpoint.

## 90% → 95% — Hardening and experiment freeze
- [ ] Secret scan, failure injection, rebuild-from-zero and duplicate schedule test.
- [ ] Dependency/recovery policy.
- [ ] Freeze cohort prompt/protocol/provider/model and checkpoint tag.

## 95% → 100% — Start forward cohort v1
- [ ] Initialize official simulated €1,000 cohort.
- [ ] Generate observation #1 prospectively and verify timestamp/evidence/hash/UI.
- [ ] Verify unattended evaluator and document frozen start configuration.

# Future gate: real money — outside this 0–100 plan

No automatic promotion to live trading. A separate design review is required after a sufficiently informative forward-simulation cohort.

## Working protocol for future chats

1. Read README and current repo state.
2. Identify completed percentage.
3. Execute only the next 5% block.
4. Run its acceptance checks.
5. Update README and mark only genuinely completed items.
6. Commit checkpoint.
7. **STOP** until the user says `sigue`.

## Current checkpoint

**25% complete.** The engine now has an external-provider-independent market-data contract, deterministic offline fixtures, quote/candle temporal models, sanitized audit snapshots and fail-closed handling for missing/stale/closed data. Alpaca Market Data is selected as the first real adapter. Next block is **25% → 30%: Real market-data adapter**.