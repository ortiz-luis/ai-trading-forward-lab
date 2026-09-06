# AI Trading Forward Lab

GitHub-first, forward-only experiment for observing how an AI manages a **simulated** portfolio over time.

> **Current progress: 15% / 100%**  
> **Current gate: STOP — waiting for explicit `sigue` before starting 20%.**

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

## Repository structure

```text
app/
engine/
  cli.py
  commands.py
  config.py
  schemas.py
  ledger.py
  portfolio.py
  providers/
data/
prompts/
tests/
docs/
.github/workflows/
pyproject.toml
README.md
```

# Master implementation plan — 0% → 100%

A block is complete only when its acceptance criteria pass.

## 0% → 5% — Project control plane and architecture freeze ✅
- [x] Public repository and README master board.
- [x] Pages + Actions + Python + OpenAI API + market adapter + ledger architecture.
- [x] Simulation-only boundary and 5% stop/go cadence.
- [x] Architecture baseline and initial skeleton.

**Acceptance:** another session can recover goal, architecture, boundaries and next task from the repo alone.

## 5% → 10% — Executable Python skeleton ✅
- [x] `pyproject.toml`, Python 3.11+, importable `engine`.
- [x] Offline `decide`, `evaluate`, `rebuild` interfaces.
- [x] Deterministic config, smoke tests and WSL/CI command.

**Acceptance:** `python -m pytest` passes offline; prior reconstructed run: **4 passed**.

## 10% → 15% — Event schemas and immutable ledger ✅
- [x] Strict `DecisionEvent` schema.
- [x] Strict `EvaluationEvent` schema.
- [x] Strict system/error event schema.
- [x] UTC canonical storage + Europe/Paris display conversion.
- [x] Append-only canonical JSONL reader/writer.
- [x] Stable deterministic `decision_id` and idempotency key.
- [x] SHA-256 locked payload hash.
- [x] Tests for round-trip, duplicate rejection, strict unknown-field rejection, NO_TRADE invariants and mutation detection.

**Acceptance:** event fixtures validate/round-trip; locked decisions detect payload mutation and duplicate IDs are rejected. Runtime network clone could not be used in this session, so the repository contains the acceptance tests to be executed by the established offline test command before any later production gate.

## 15% → 20% — Portfolio accounting engine
- [ ] Starting simulated capital (€1,000 default/configurable).
- [ ] Cash, equity, open positions, realized/unrealized P&L.
- [ ] BUY/HOLD/SELL/NO_TRADE transitions.
- [ ] No leverage, non-negative cash, exposure limits.
- [ ] Rebuild portfolio entirely from ledger events.
- [ ] Accounting invariant tests.

**Acceptance:** deleting derived portfolio state and rebuilding from ledger yields equivalent state.

## 20% → 25% — Market-data provider abstraction
- [ ] `MarketDataProvider` interface + deterministic fixture provider.
- [ ] Select first external provider.
- [ ] Quote/candle timestamp model and audit cache.
- [ ] Explicit stale/missing/closed-market behavior.

**Acceptance:** fixture input is deterministic and stale data cannot create a trade.

## 25% → 30% — Real market-data adapter
- [ ] External adapter via environment secret.
- [ ] Small allowed universe; normalized symbols/timestamps/currencies.
- [ ] Retry/rate-limit and health handling; no persisted secrets.

**Acceptance:** sanitized timestamped snapshot or explicit failure.

## 30% → 35% — Trading protocol v1
- [ ] Freeze universe, long-only/no-leverage constraints and position limits.
- [ ] Freeze sizing/exposure, horizon/stop, entry/exit and benchmark rules.
- [ ] Define `NO_TRADE` conditions.

**Acceptance:** deterministic implementations agree on allowed actions/outcomes.

## 35% → 40% — OpenAI decision contract
- [ ] `prompts/trading_v1.md` + strict structured-output schema.
- [ ] Portfolio/cutoff/context input; thesis/counter-thesis/confidence/sources output.
- [ ] Prohibit post-cutoff information; first-class `NO_TRADE`.
- [ ] Prompt/model versions and fixtures.

**Acceptance:** every fixture validates exactly or fails closed.

## 40% → 45% — OpenAI API integration
- [ ] Official SDK behind `DecisionProvider`.
- [ ] Key only from environment/GitHub Secret.
- [ ] Timeout/bounded retry, one controlled repair, explicit `AI_ERROR`.
- [ ] Cost metadata where available; failure never becomes `NO_TRADE`.

**Acceptance:** schema-valid decision or explicit failure, never ambiguous free text.

## 45% → 50% — Context and evidence pipeline
- [ ] Evidence object with URL/source/publication/retrieval times.
- [ ] Prioritize primary sources; bounded recent-news/search context.
- [ ] Prevent stale evidence appearing current; persist evidence manifest.

**Acceptance:** every decision can show evidence available at cutoff.

## 50% → 55% — Deterministic evaluator
- [ ] Entry, stop, expiry and SELL rules.
- [ ] Configurable costs/slippage; gross/net P&L and benchmark.
- [ ] Evaluation event never alters decision event.

**Acceptance:** fixtures yield verified win/loss/stop/expiry outcomes.

## 55% → 60% — Scoring and statistics
- [ ] Human-readable points; wins/losses/no-trades/errors separately.
- [ ] Equity, benchmark, drawdown and confidence calibration.
- [ ] Points never substitute monetary P&L.

**Acceptance:** all statistics reproduce from ledger + observations.

## 60% → 65% — GitHub Actions automation core
- [ ] Daily schedule + `workflow_dispatch`.
- [ ] Timezone-aware actual timestamp, concurrency guard and idempotency.
- [ ] Controlled decision/validation/persistence/tests pipeline.

**Acceptance:** repeated same-day execution cannot duplicate a decision.

## 65% → 70% — Evaluation automation and resilience
- [ ] Periodic unattended evaluator and bounded retries.
- [ ] `DATA_ERROR`, `AI_ERROR`, `DEPLOY_ERROR`, `health.json`.
- [ ] Preserve prior site on failed build; synthetic multi-day test.

**Acceptance:** injected failures do not corrupt state.

## 70% → 75% — Public-data build layer
- [ ] Sanitized dashboard JSON, no secret serialization.
- [ ] “Mientras no estuviste”, current portfolio, equity series, latest cards.
- [ ] Secret-pattern scan.

**Acceptance:** public artifacts contain everything UI needs and nothing secret.

## 75% → 80% — Beginner-first GitHub Pages UI
- [ ] Responsive home page.
- [ ] Hero: starting money → current money → gain/loss.
- [ ] Simple latest decision, open positions, green/red/neutral history.
- [ ] “Mientras no estuviste” + one cumulative equity chart.

**Acceptance:** first-time user understands what happened in under 10 seconds.

## 80% → 85% — Pages deployment and manual interaction
- [ ] Official Pages deployment and correct base path.
- [ ] Authorized manual “request a decision now”.
- [ ] Health/update status, mobile/desktop and HTTPS validation.

**Acceptance:** public site works without exposing credentials.

## 85% → 90% — Optional Alpaca Paper shadow execution
- [ ] Paper-only broker adapter and credentials.
- [ ] Mirror eligible simulated orders and reconcile fills.
- [ ] Never overwrite internal ledger; hard-block live endpoint.

**Acceptance:** Alpaca Paper is optional and internal truth remains reproducible.

## 90% → 95% — Hardening and experiment freeze
- [ ] Secret scan, failure injection, rebuild-from-zero, duplicate schedule test.
- [ ] Dependency/recovery policy.
- [ ] Freeze cohort prompt/protocol/provider/model and create checkpoint tag.

**Acceptance:** no known path silently edits history, exposes keys, spends unbounded API budget or trades from missing data.

## 95% → 100% — Start forward cohort v1
- [ ] Initialize official simulated €1,000 cohort.
- [ ] Generate observation #1 prospectively and verify timestamp/evidence/hash/UI.
- [ ] Verify unattended evaluator and document frozen start configuration.

**Acceptance:** experiment can run for days without the user and honestly answer what ChatGPT would have done and how much money would remain.

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

**15% complete.** Strict event schemas and immutable append-only ledger primitives are in place. Next block is **15% → 20%: Portfolio accounting engine**.