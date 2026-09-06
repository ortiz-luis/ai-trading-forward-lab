# AI Trading Forward Lab

GitHub-first, forward-only experiment for observing how an AI manages a **simulated** portfolio over time.

> **Current progress: 10% / 100%**  
> **Current gate: STOP — waiting for explicit `sigue` before starting 15%.**

## Product goal

Build a low-friction hobby project that continues running when the user is absent. A scheduled workflow gathers market context, OpenAI receives a fixed/versioned protocol, the model chooses `BUY`, `HOLD`, `SELL`, or `NO_TRADE`, the decision is timestamped and locked, deterministic code calculates the simulated portfolio, and a public GitHub Pages dashboard answers: **we started with €1,000; how much would we have now?**

## Non-negotiable rules

- Phase 1 uses **no real money** and no live-broker credentials.
- Forward-only: no retroactive rewriting of predictions.
- The AI makes the decision; deterministic code calculates accounting and P&L.
- `NO_TRADE` is valid and is not a failure.
- API keys never appear in browser code, repository data, Pages artifacts or logs.
- GitHub Pages is the public UI; GitHub Actions is the scheduled execution layer.
- Unattended AI calls use the OpenAI API, not browser automation of chatgpt.com.
- Each cohort freezes prompt, universe, sizing, timing and evaluation rules before observation #1.
- Work advances in exact **5% gates** and stops after each gate until the user says **`sigue`**.

## Target architecture

```text
User
  ↓
GitHub Pages  ← generated public data
  ↑
GitHub Actions scheduler / manual dispatch
  ↓
Python engine
  ├── Market data adapter
  ├── Context builder
  ├── OpenAI Responses API
  ├── Schema validator
  ├── Portfolio rules
  ├── Append-only ledger
  └── Deterministic evaluator
              ↓
       Git-versioned state
              ↓
         Pages rebuild
```

## Repository target structure

```text
/
├── app/
├── engine/
│   ├── cli.py
│   ├── commands.py
│   ├── config.py
│   ├── decide.py
│   ├── evaluate.py
│   ├── portfolio.py
│   ├── schemas.py
│   └── providers/
├── data/
│   ├── decisions.jsonl
│   ├── evaluations.jsonl
│   ├── portfolio.json
│   └── public/
├── prompts/trading_v1.md
├── tests/
├── docs/
├── .github/workflows/
├── pyproject.toml
└── README.md
```

# Master implementation plan — 0% → 100%

Each block is an acceptance gate. A block is complete only when its acceptance criteria pass.

## 0% → 5% — Project control plane and architecture freeze ✅

- [x] Create public repository.
- [x] Establish README as master TODO/progress board.
- [x] Freeze Pages + Actions + Python + OpenAI API + market-data adapter + append-only ledger architecture.
- [x] Freeze simulation-only safety boundary.
- [x] Define 5% stop/go cadence.
- [x] Add architecture baseline under `docs/`.
- [x] Add initial project skeleton.

**Acceptance:** another session can recover goal, architecture, boundaries, next task and stop condition from the repo alone.

---

## 5% → 10% — Executable Python skeleton ✅

- [x] Add `pyproject.toml` with Python 3.11+ and minimal dependencies.
- [x] Create importable `engine` package.
- [x] Define offline top-level interfaces for `decide`, `evaluate`, and `rebuild`.
- [x] Add deterministic configuration loader.
- [x] Add smoke tests.
- [x] Document one-command test entry point for WSL/CI in `docs/LOCAL_DEVELOPMENT.md`.

**Acceptance:** `python -m pytest` passes with no secrets and no network. Local reconstructed acceptance run: **4 passed**. Smoke commands are `python -m engine.cli decide|evaluate|rebuild`.

---

## 10% → 15% — Event schemas and immutable ledger

- [ ] Define strict `DecisionEvent` schema.
- [ ] Define strict `EvaluationEvent` schema.
- [ ] Define system/error event schema.
- [ ] Establish canonical timestamps: UTC storage + Europe/Paris display.
- [ ] Implement append-only JSONL writer.
- [ ] Implement stable `decision_id` and idempotency key.
- [ ] Implement locked payload hash.
- [ ] Add tests proving original decisions cannot be silently mutated.

**Acceptance:** demo events round-trip, validate, hash, reload and reject illegal mutations.

---

## 15% → 20% — Portfolio accounting engine

- [ ] Starting simulated capital (€1,000 default/configurable).
- [ ] Cash, equity, open positions, realized/unrealized P&L.
- [ ] BUY/HOLD/SELL/NO_TRADE transitions.
- [ ] No leverage and non-negative cash.
- [ ] Per-position and total-exposure limits.
- [ ] Rebuild portfolio entirely from ledger events.
- [ ] Accounting invariant tests.

**Acceptance:** deleting derived portfolio state and rebuilding from ledger yields equivalent state.

---

## 20% → 25% — Market-data provider abstraction

- [ ] Define `MarketDataProvider` interface.
- [ ] Deterministic fixture provider.
- [ ] Select first external provider.
- [ ] Quote/candle timestamp model.
- [ ] Cache observations needed for audit/replay.
- [ ] Explicit missing/stale/closed-market behavior.

**Acceptance:** fixture input always gives same normalized snapshot and stale data cannot create a trade.

---

## 25% → 30% — Real market-data adapter

- [ ] External adapter using environment secret.
- [ ] Quotes for small allowed universe.
- [ ] Normalize symbols/timestamps/currencies.
- [ ] Retry/rate-limit behavior.
- [ ] Provider health status.
- [ ] Ensure secrets never persist.

**Acceptance:** manual network run produces sanitized timestamped snapshot or clean explicit failure.

---

## 30% → 35% — Trading protocol v1

- [ ] Freeze asset universe.
- [ ] Freeze long-only/no-leverage phase-1 constraints.
- [ ] Freeze simultaneous-position limit.
- [ ] Freeze sizing/exposure limits.
- [ ] Freeze horizon/stop semantics.
- [ ] Freeze entry/exit price rules.
- [ ] Freeze benchmark.
- [ ] Define `NO_TRADE` conditions.

**Acceptance:** protocol is precise enough for two deterministic implementations to agree on allowed actions/outcomes.

---

## 35% → 40% — OpenAI decision contract

- [ ] Create `prompts/trading_v1.md`.
- [ ] Strict structured-output schema.
- [ ] Include portfolio, cutoff and market context.
- [ ] Require thesis, counter-thesis, confidence and sources.
- [ ] Prohibit post-cutoff information.
- [ ] Make `NO_TRADE` first-class.
- [ ] Record prompt/model versions.
- [ ] Fixtures for every action/error path.

**Acceptance:** every fixture validates exactly or fails closed.

---

## 40% → 45% — OpenAI API integration

- [ ] Official OpenAI SDK behind `DecisionProvider`.
- [ ] API key only from environment/GitHub Secret.
- [ ] Timeout and bounded retry.
- [ ] One controlled structured-output repair attempt.
- [ ] Explicit `AI_ERROR`.
- [ ] Cost/usage metadata where available.
- [ ] API failure can never become `NO_TRADE`.

**Acceptance:** invocation returns schema-valid decision or explicit failure, never ambiguous free text.

---

## 45% → 50% — Context and evidence pipeline

- [ ] Evidence object: URL/source/publication/retrieval time.
- [ ] Prioritize primary corporate/regulatory sources.
- [ ] Bounded recent-news/search context.
- [ ] Prevent stale evidence appearing current.
- [ ] Persist auditable evidence manifest.
- [ ] Bound context size/cost.

**Acceptance:** every decision can show evidence available at cutoff.

---

## 50% → 55% — Deterministic evaluator

- [ ] Entry rule.
- [ ] Stop evaluation.
- [ ] Horizon expiry.
- [ ] Explicit SELL evaluation.
- [ ] Configurable costs/slippage.
- [ ] Gross/net P&L.
- [ ] Benchmark over same window.
- [ ] Evaluation event without altering decision event.

**Acceptance:** known price fixtures yield verified win/loss/stop/expiry outcomes.

---

## 55% → 60% — Scoring and experiment statistics

- [ ] Human-readable points system.
- [ ] Wins/losses/no-trades/errors separately.
- [ ] Cumulative equity.
- [ ] Return vs benchmark.
- [ ] Maximum drawdown.
- [ ] Confidence calibration buckets.
- [ ] Points never substitute monetary P&L.

**Acceptance:** statistics reproduce exactly from ledger + observations.

---

## 60% → 65% — GitHub Actions automation core

- [ ] Daily scheduled workflow.
- [ ] `workflow_dispatch` manual trigger.
- [ ] Timezone-aware scheduling and actual timestamp.
- [ ] Concurrency guard.
- [ ] Date/session idempotency.
- [ ] Controlled decision/validation/persistence/tests pipeline.
- [ ] Commit only sanitized artifacts.

**Acceptance:** repeated same-day execution cannot duplicate a decision.

---

## 65% → 70% — Evaluation automation and resilience

- [ ] Periodic evaluator workflow.
- [ ] Update open positions unattended.
- [ ] Bounded retries.
- [ ] `DATA_ERROR`, `AI_ERROR`, `DEPLOY_ERROR` events.
- [ ] `health.json`.
- [ ] Preserve prior site on failed build.
- [ ] Synthetic unattended multi-day test.

**Acceptance:** injected API/provider failures do not corrupt state.

---

## 70% → 75% — Public-data build layer

- [ ] Sanitized dashboard JSON.
- [ ] No environment/secret serialization.
- [ ] “Mientras no estuviste” feed.
- [ ] Current portfolio summary.
- [ ] Historical equity series.
- [ ] Latest decision/result cards.
- [ ] Secret-pattern scan.

**Acceptance:** public data contains everything UI needs and nothing secret.

---

## 75% → 80% — Beginner-first GitHub Pages UI

- [ ] Responsive home page.
- [ ] Hero: starting money → current simulated money → gain/loss.
- [ ] Last AI decision in ordinary language.
- [ ] Simple open positions.
- [ ] Green/red/neutral history cards.
- [ ] “Mientras no estuviste”.
- [ ] One cumulative equity chart.
- [ ] Advanced metrics secondary.

**Acceptance:** first-time user understands what happened in under 10 seconds.

---

## 80% → 85% — Pages deployment and manual interaction

- [ ] Official Pages deployment workflow.
- [ ] Correct project Pages base path.
- [ ] Authorized manual “request a decision now” path.
- [ ] Last update and health status in UI.
- [ ] Mobile/desktop validation.
- [ ] HTTPS/public-access validation.

**Acceptance:** main branch deploys working public site and manual execution exposes no credentials.

---

## 85% → 90% — Optional Alpaca Paper shadow execution

- [ ] Paper-broker adapter boundary.
- [ ] Alpaca paper-only credentials.
- [ ] Mirror eligible simulated orders.
- [ ] Reconcile internal theoretical vs paper fills.
- [ ] Display discrepancies without overwriting internal ledger.
- [ ] Hard-block live endpoint/credentials.

**Acceptance:** paper broker is optional and internal truth remains reproducible.

---

## 90% → 95% — Hardening and experiment freeze

- [ ] Secret scan across repo/site.
- [ ] Failure-injection suite.
- [ ] Rebuild-from-zero test.
- [ ] Duplicate-schedule test.
- [ ] Dependency/update policy.
- [ ] Recovery procedure.
- [ ] Freeze prompt/protocol/provider/model cohort configuration.
- [ ] Create pre-experiment tag/checkpoint.

**Acceptance:** no known path silently edits history, exposes keys, spends unbounded API budget or creates trades from missing data.

---

## 95% → 100% — Start forward cohort v1

- [ ] Initialize official simulated €1,000 cohort.
- [ ] Generate observation #1 prospectively.
- [ ] Verify timestamp/evidence/hash.
- [ ] Verify dashboard display.
- [ ] Verify unattended evaluator.
- [ ] Document start date/frozen configuration.
- [ ] Declare v1 live in simulation-only mode.

**Acceptance:** the experiment can run for days without the user and honestly answer “what would ChatGPT have done, and how much would we have now?”

---

# Future gate: real money — outside this 0–100 plan

No automatic promotion to live trading. A separate design review is required after a sufficiently informative forward-simulation cohort.

## Working protocol for future chats

1. Read this README and current repository state first.
2. Identify the completed percentage.
3. Execute only the next 5% block.
4. Run its acceptance checks.
5. Update README and mark only genuinely completed items.
6. Commit checkpoint.
7. **STOP** until the user says `sigue`.

## Current checkpoint

**10% complete.** Executable offline Python skeleton is in place and smoke-tested. Next block is **10% → 15%: Event schemas and immutable ledger**.