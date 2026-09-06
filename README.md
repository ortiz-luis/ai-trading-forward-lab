# AI Trading Forward Lab

GitHub-first, forward-only experiment for observing how an AI manages a **simulated** portfolio over time.

> **Current progress: 5% / 100%**  
> **Current gate: STOP — waiting for explicit `sigue` before starting 10%.**

## Product goal

Build a low-friction hobby project where the system can continue running even when the user is absent:

1. A scheduled workflow gathers current market context.
2. OpenAI receives a fixed, versioned decision protocol.
3. The model must choose `BUY`, `HOLD`, `SELL`, or `NO_TRADE` within hard portfolio limits.
4. The decision is timestamped and locked before the outcome is known.
5. Deterministic code tracks the simulated position and later evaluates the result.
6. A simple public GitHub Pages dashboard answers: **we started with €1,000; how much would we have now?**
7. Every win, loss, no-trade day, API failure, and model decision remains visible and auditable.

## Non-negotiable rules

- Phase 1 uses **no real money** and no live-broker credentials.
- Forward-only. No retroactive rewriting of predictions.
- The AI makes the decision; deterministic code calculates accounting and P&L.
- `NO_TRADE` is a valid result and must never be treated as a failure.
- API keys never appear in the browser, repository, Pages artifacts, or logs.
- GitHub Pages is the public UI; GitHub Actions is the scheduled execution layer.
- The unattended AI integration uses the OpenAI API, not browser automation of a personal chatgpt.com session.
- Each experimental cohort freezes its prompt, universe, sizing rules, timing, and evaluation rules before observation #1.
- Work advances in exact **5% gates**. After each gate, stop until the user explicitly says **`sigue`**.

## Target architecture

```text
User
  ↓
GitHub Pages  ← reads generated public data
  ↑
GitHub Actions scheduler / manual dispatch
  ↓
Python decision engine
  ├── Market data adapter
  ├── Context builder
  ├── OpenAI Responses API
  ├── Schema validator
  ├── Portfolio rules
  ├── Append-only decision ledger
  └── Deterministic evaluator
              ↓
       Git-versioned state
              ↓
         Pages rebuild
```

## Repository target structure

```text
/
├── app/                     # static dashboard frontend
├── engine/                  # deterministic Python core
│   ├── decide.py
│   ├── evaluate.py
│   ├── portfolio.py
│   ├── schemas.py
│   └── providers/
├── data/
│   ├── decisions.jsonl      # immutable decision events
│   ├── evaluations.jsonl    # outcome events
│   ├── portfolio.json       # derived/cache state
│   └── public/              # sanitized data consumed by Pages
├── prompts/
│   └── trading_v1.md
├── tests/
├── docs/
├── .github/workflows/
└── README.md
```

# Master implementation plan — 0% → 100%

Each block is an acceptance gate. A block is not marked complete because files exist; its acceptance criteria must pass.

## 0% → 5% — Project control plane and architecture freeze ✅

- [x] Create public repository `ortiz-luis/ai-trading-forward-lab`.
- [x] Establish this README as the single master TODO/progress board.
- [x] Freeze the v1 architectural direction: Pages + Actions + Python + OpenAI API + market-data adapter + append-only ledger.
- [x] Freeze phase-1 safety boundary: simulation only, no live broker credentials.
- [x] Define exact 5% stop/go working cadence.
- [x] Add architecture baseline document under `docs/`.
- [x] Add minimal project skeleton placeholders so subsequent gates have stable locations.

**Acceptance gate:** another implementation session can determine the goal, architecture, boundaries, next task and stop condition from the repository alone.

---

## 5% → 10% — Executable Python skeleton

- [ ] Add `pyproject.toml` with supported Python version and minimal dependencies.
- [ ] Create importable `engine` package.
- [ ] Define top-level commands/interfaces for `decide`, `evaluate`, and `rebuild` without external API calls.
- [ ] Add deterministic configuration loader.
- [ ] Add first smoke tests.
- [ ] Add local one-command test entry point suitable for WSL and CI.

**Acceptance gate:** fresh clone → one documented command → tests pass with no secrets and no network.

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

**Acceptance gate:** demo events round-trip, validate, hash, reload and reject illegal mutations.

---

## 15% → 20% — Portfolio accounting engine

- [ ] Define starting simulated capital (€1,000 default, configurable).
- [ ] Implement cash, equity, open positions and realized/unrealized P&L.
- [ ] Implement BUY/HOLD/SELL/NO_TRADE state transitions.
- [ ] Enforce no leverage and non-negative cash.
- [ ] Enforce maximum per-position and total-exposure rules.
- [ ] Rebuild portfolio entirely from ledger events.
- [ ] Add accounting invariant tests.

**Acceptance gate:** deleting derived `portfolio.json` and rebuilding from events yields bit-for-bit equivalent state.

---

## 20% → 25% — Market-data provider abstraction

- [ ] Define `MarketDataProvider` interface.
- [ ] Implement deterministic fixture provider for tests.
- [ ] Select first official external data provider.
- [ ] Implement quote/candle timestamp model.
- [ ] Cache raw observations needed for audit/replay.
- [ ] Handle missing/stale/closed-market data explicitly.

**Acceptance gate:** same fixture inputs always produce same normalized market snapshot; stale data cannot create a trade.

---

## 25% → 30% — Real market-data adapter

- [ ] Implement selected provider adapter using secret from environment.
- [ ] Retrieve quotes for a small allowed universe.
- [ ] Normalize symbols, timestamps and currencies.
- [ ] Add retry/rate-limit behavior.
- [ ] Add provider health status.
- [ ] Ensure secrets never enter persisted snapshots.

**Acceptance gate:** manual network run produces a sanitized, timestamped market snapshot and clean failure when secret/API is unavailable.

---

## 30% → 35% — Trading protocol v1

- [ ] Freeze initial asset universe.
- [ ] Freeze long-only / no-leverage phase-1 constraints.
- [ ] Freeze maximum number of simultaneous positions.
- [ ] Freeze sizing range and exposure limits.
- [ ] Freeze horizon and stop semantics.
- [ ] Freeze entry-price and exit-price rules.
- [ ] Freeze benchmark (initially SPY unless changed before cohort start).
- [ ] Define when the correct action is `NO_TRADE`.

**Acceptance gate:** protocol is precise enough that two deterministic implementations would calculate the same allowed actions and outcomes.

---

## 35% → 40% — OpenAI decision contract

- [ ] Create `prompts/trading_v1.md`.
- [ ] Define strict structured-output JSON schema.
- [ ] Include portfolio state, cutoff timestamp and market context.
- [ ] Require thesis, counter-thesis, confidence and sources.
- [ ] Explicitly prohibit information after cutoff.
- [ ] Make `NO_TRADE` first-class.
- [ ] Record prompt version and model identifier.
- [ ] Add fixture responses for every action/error path.

**Acceptance gate:** 100% of fixture outputs either validate exactly or fail closed without creating a decision.

---

## 40% → 45% — OpenAI API integration

- [ ] Add official OpenAI SDK integration behind `DecisionProvider`.
- [ ] Read API key only from environment/GitHub Secret.
- [ ] Add timeout and bounded retry.
- [ ] Add one controlled structured-output repair attempt if needed.
- [ ] Add explicit `AI_ERROR` state.
- [ ] Add API cost/usage metadata where available, without storing secrets.
- [ ] Prevent an API failure from becoming `NO_TRADE`.

**Acceptance gate:** manual invocation returns a schema-valid decision or explicit failure, never ambiguous free text.

---

## 45% → 50% — Context and evidence pipeline

- [ ] Define evidence object with URL/source/publication time/retrieval time.
- [ ] Prioritize primary corporate/regulatory sources where practical.
- [ ] Add bounded recent-news/search context.
- [ ] Prevent undated/stale evidence from silently appearing current.
- [ ] Persist a minimal auditable evidence manifest per decision.
- [ ] Keep context size/cost bounded.

**Acceptance gate:** every AI decision can show what evidence was available at its cutoff time.

---

## 50% → 55% — Deterministic evaluator

- [ ] Implement entry execution rule.
- [ ] Implement stop evaluation.
- [ ] Implement horizon expiry.
- [ ] Implement explicit SELL evaluation.
- [ ] Implement configurable simulated costs/slippage assumptions.
- [ ] Calculate gross/net P&L.
- [ ] Calculate benchmark return over identical window.
- [ ] Create evaluation event without altering decision event.

**Acceptance gate:** known price fixtures yield mathematically verified outcomes for win, loss, stop and expiry cases.

---

## 55% → 60% — Scoring and experiment statistics

- [ ] Define human-readable points system.
- [ ] Track wins/losses/no-trades/errors separately.
- [ ] Track cumulative simulated equity.
- [ ] Track return vs benchmark.
- [ ] Track maximum drawdown.
- [ ] Track confidence calibration buckets.
- [ ] Ensure points never substitute for monetary P&L.

**Acceptance gate:** statistics reproduce exactly from ledger + market observations, with no manually edited totals.

---

## 60% → 65% — GitHub Actions automation core

- [ ] Add daily scheduled workflow.
- [ ] Add `workflow_dispatch` manual trigger.
- [ ] Use timezone-aware scheduling and record actual execution timestamp.
- [ ] Add concurrency guard.
- [ ] Add per-session/date idempotency.
- [ ] Run decision, validation, persistence and tests in one controlled pipeline.
- [ ] Commit only sanitized public/state artifacts.

**Acceptance gate:** repeated same-day execution cannot create duplicate decision events.

---

## 65% → 70% — Evaluation automation and resilience

- [ ] Add periodic evaluator workflow.
- [ ] Update open positions without requiring user presence.
- [ ] Add bounded retries for external providers.
- [ ] Add `DATA_ERROR`, `AI_ERROR`, `DEPLOY_ERROR` events.
- [ ] Add `health.json`.
- [ ] Preserve previous public site if a new build fails.
- [ ] Test several days of synthetic unattended execution.

**Acceptance gate:** simulated multi-day run survives injected provider/API failures without corrupting state.

---

## 70% → 75% — Public-data build layer

- [ ] Generate sanitized dashboard JSON from private/runtime state.
- [ ] Ensure no secret/environment value is serialized.
- [ ] Generate “while you were away” feed.
- [ ] Generate current portfolio summary.
- [ ] Generate historical equity series.
- [ ] Generate latest decision/result cards.
- [ ] Add automated secret-pattern scan of publishable artifacts.

**Acceptance gate:** public data contains everything UI needs and nothing secret.

---

## 75% → 80% — Beginner-first GitHub Pages UI

- [ ] Build responsive home page.
- [ ] Hero: starting money → current simulated money → gain/loss.
- [ ] Show last AI decision in ordinary language.
- [ ] Show open positions simply.
- [ ] Show green/red/neutral history cards.
- [ ] Show “Mientras no estuviste”.
- [ ] Show one clear cumulative equity chart.
- [ ] Keep advanced metrics below/behind secondary view.

**Acceptance gate:** a first-time user can explain what happened in under 10 seconds without reading documentation.

---

## 80% → 85% — Pages deployment and manual interaction

- [ ] Add official GitHub Pages deployment workflow.
- [ ] Configure base path correctly for project Pages.
- [ ] Add manual “request a decision now” path through authorized GitHub workflow, not a public API-key endpoint.
- [ ] Surface last system update and health status in UI.
- [ ] Validate mobile/desktop rendering.
- [ ] Validate HTTPS/public access behavior.

**Acceptance gate:** main branch produces a working public site; manual execution is possible without exposing credentials.

---

## 85% → 90% — Optional Alpaca Paper shadow execution

- [ ] Create adapter boundary for paper broker.
- [ ] Support Alpaca **paper-only** credentials.
- [ ] Mirror eligible simulated orders to paper environment.
- [ ] Reconcile internal theoretical fills vs paper fills.
- [ ] Display differences instead of overwriting internal ledger.
- [ ] Hard-block live endpoint/credentials in phase 1.

**Acceptance gate:** paper broker can be disabled entirely; when enabled, discrepancies are visible and internal truth remains reproducible.

---

## 90% → 95% — Hardening and experiment freeze

- [ ] Run secret scan across repo and built site.
- [ ] Run failure-injection suite.
- [ ] Run rebuild-from-zero test.
- [ ] Run duplicate-schedule test.
- [ ] Check dependency/update policy.
- [ ] Document recovery procedure.
- [ ] Freeze prompt/protocol/provider/model cohort configuration.
- [ ] Create pre-experiment tag/checkpoint.

**Acceptance gate:** no known path silently edits history, spends unbounded API budget, exposes keys, or creates trades from missing data.

---

## 95% → 100% — Start forward cohort v1

- [ ] Initialize official simulated €1,000 cohort.
- [ ] Generate observation #1 prospectively.
- [ ] Verify its timestamp/evidence/hash in repository.
- [ ] Verify dashboard displays it correctly.
- [ ] Verify evaluator can follow it unattended.
- [ ] Document cohort start date and frozen configuration.
- [ ] Declare v1 live in **simulation-only** mode.

**Acceptance gate:** the experiment can continue for days without the user and return an honest, auditable answer to “what would ChatGPT have done, and how much would we have now?”

---

# Future gate: real money — explicitly outside this 0–100 plan

No automatic promotion to live trading exists. A separate design review is required after a sufficiently informative forward-simulation cohort. Paper results do not guarantee live results because real execution adds slippage, latency, market impact, liquidity constraints and behavioral effects.

## Working protocol for future chats

1. Read this README and current repository state first.
2. Identify the current completed percentage.
3. Execute only the next 5% block.
4. Run its acceptance checks.
5. Update this README and mark only genuinely completed items.
6. Commit the checkpoint.
7. **STOP.** Do not begin the following block until the user says `sigue`.

## Current checkpoint

**5% complete.** Project architecture and execution order are frozen. Next block is **5% → 10%: Executable Python skeleton**.