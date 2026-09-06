# AI Trading Forward Lab

GitHub-first, forward-only experiment for observing how an AI manages a **simulated** portfolio over time.

> **Current progress: 50% / 100%**  
> **Current gate: STOP — waiting for explicit `sigue` before starting 55%.**

## Product goal

Build a low-friction hobby project that keeps running while the user is away: scheduled market context → fixed/versioned OpenAI decision → timestamped locked event → deterministic simulated accounting → simple public dashboard answering **“we started with €1,000; how much would we have now?”**

## Non-negotiable rules

- Phase 1: **no real money** and no live-broker credentials.
- Forward-only; no retroactive rewriting.
- AI decides; deterministic code calculates accounting/P&L.
- `NO_TRADE` is valid, but data/AI failures are never relabeled `NO_TRADE`.
- Keys never appear in browser, repository data, Pages artifacts or logs.
- GitHub Pages = public UI; GitHub Actions = scheduled execution.
- Unattended AI uses OpenAI API, not browser automation of chatgpt.com.
- Each cohort freezes prompt, universe, sizing, timing, evidence and evaluation rules before observation #1.
- Work advances in exact **5% gates** and stops until the user says `sigue`.

# Master implementation plan — 0% → 100%

A block is complete only when its acceptance criteria pass.

## 0% → 5% — Project control plane and architecture freeze ✅
- [x] Public repository and README master board.
- [x] Pages + Actions + Python + OpenAI API + market adapter + append-only ledger architecture.
- [x] Simulation-only boundary and 5% stop/go cadence.
- [x] Architecture baseline and initial skeleton.

## 5% → 10% — Executable Python skeleton ✅
- [x] Python 3.11+ package, deterministic config, offline CLI and smoke tests.

## 10% → 15% — Event schemas and immutable ledger ✅
- [x] Strict decision/evaluation/system schemas, UTC timestamps, deterministic IDs/idempotency, JSONL ledger and SHA-256 locked decisions.

## 15% → 20% — Portfolio accounting engine ✅
- [x] €1,000 configurable start, cash/equity/positions/P&L fields, BUY/HOLD/SELL/NO_TRADE transitions, exposure guards and ledger replay.

## 20% → 25% — Market-data provider abstraction ✅
- [x] Provider contract, deterministic fixture, quote/candle models, audit snapshots and fail-closed stale/missing/closed handling.

## 25% → 30% — Real market-data adapter ✅
- [x] Alpaca Market Data adapter with environment-only credentials, quote/bar normalization, retries, health state and safe probe.

## 30% → 35% — Trading protocol v1 ✅
- [x] Liquid US-equity universe; SPY benchmark.
- [x] Long-only, no leverage/short/options/futures/CFDs/crypto.
- [x] Max 3 positions, 15% per position, 45% total exposure.
- [x] Stop bounds -1% to -5%, horizon 2–10 trading days, forward-only entry and explicit `NO_TRADE` rules.
- [x] Human-readable and machine-readable frozen protocol.

## 35% → 40% — OpenAI decision contract ✅
- [x] Versioned prompt, strict Structured Output schema and cutoff-aware input.
- [x] Output requires action, simulated notional, confidence, horizon, stop, thesis/counter-thesis and sources.
- [x] Post-cutoff facts and invented facts prohibited; outputs validated against protocol v1.

## 40% → 45% — OpenAI API integration ✅
- [x] Official OpenAI SDK / Responses API behind `OpenAIDecisionProvider`.
- [x] `OPENAI_API_KEY` only from runtime environment/GitHub Secret.
- [x] Configurable model, strict JSON schema, `store=false`, bounded timeout/retries and one repair attempt.
- [x] Explicit `AI_ERROR`; double failure never becomes `NO_TRADE`.
- [x] Response/model/token metadata and synthetic probe/tests.

## 45% → 50% — Context and evidence pipeline ✅
- [x] `EvidenceRecord` carries URL, source name/class, title, publication time, retrieval time and summary.
- [x] Primary sources rank before secondary sources.
- [x] Default bounded context: maximum 12 evidence items.
- [x] Default freshness: primary ≤7 days; secondary ≤72 hours.
- [x] Undated, stale, post-cutoff publication and post-cutoff retrieval fail closed.
- [x] Deterministic ordering: source class → newest publication → URL tie-breaker.
- [x] Audit manifest records exact evidence set, cutoff and canonical SHA-256.
- [x] Manifest contains public evidence metadata only; secrets/headers/provider state are excluded.
- [x] Evidence failures remain data/context failures and are not silently converted to `NO_TRADE`.
- [x] Tests cover primary priority, deterministic bounds, stale/undated/post-cutoff rejection and stable manifest hashing.
- [x] Policy documented in `docs/EVIDENCE_PIPELINE.md`.

**Acceptance:** a decision context can be reconstructed from a bounded, deterministic evidence set whose contents were known no later than the locked cutoff. The exact set can be audited later through its manifest/hash.

## 50% → 55% — Deterministic evaluator
- [ ] Implement forward-only entry-price rule.
- [ ] Implement stop handling and horizon expiry.
- [ ] Implement explicit SELL closure.
- [ ] Add configurable simulated costs/slippage assumptions.
- [ ] Calculate gross and net P&L.
- [ ] Calculate SPY benchmark over the identical window.
- [ ] Create evaluation events without altering original decision events.
- [ ] Add fixtures for win/loss/stop/expiry paths.

**Acceptance:** known price fixtures produce mathematically verified outcomes while original locked decisions remain unchanged.

## 55% → 60% — Scoring and statistics
- [ ] Human-readable points; wins/losses/no-trades/errors separately.
- [ ] Equity, benchmark, drawdown and confidence calibration.
- [ ] Points never substitute monetary P&L.

## 60% → 65% — GitHub Actions automation core
- [ ] Daily schedule + `workflow_dispatch`.
- [ ] Timezone-aware actual timestamp, concurrency guard and date/session idempotency.
- [ ] Controlled context → AI → validation → persistence → tests pipeline.

## 65% → 70% — Evaluation automation and resilience
- [ ] Periodic unattended evaluator and bounded retries.
- [ ] `DATA_ERROR`, `AI_ERROR`, `DEPLOY_ERROR`, `health.json`.
- [ ] Preserve prior site on failed build; synthetic multi-day failure test.

## 70% → 75% — Public-data build layer
- [ ] Sanitized dashboard JSON and no secret serialization.
- [ ] “Mientras no estuviste”, current portfolio, equity series and latest cards.
- [ ] Secret-pattern scan.

## 75% → 80% — Beginner-first GitHub Pages UI
- [ ] Responsive home page.
- [ ] Hero: starting money → current money → gain/loss.
- [ ] Simple latest decision, positions, green/red/neutral history and cumulative equity chart.

## 80% → 85% — Pages deployment and manual interaction
- [ ] Official Pages deployment and correct project base path.
- [ ] Authorized manual “request a decision now”.
- [ ] Health/update status, mobile/desktop and HTTPS validation.

## 85% → 90% — Optional Alpaca Paper shadow execution
- [ ] Paper-only broker adapter and credentials.
- [ ] Mirror eligible simulated orders and reconcile fills.
- [ ] Never overwrite internal ledger; hard-block live endpoint.

## 90% → 95% — Hardening and experiment freeze
- [ ] Secret scan, failure injection, rebuild-from-zero and duplicate schedule test.
- [ ] Dependency/recovery policy.
- [ ] Freeze cohort prompt/protocol/provider/model/evidence settings and checkpoint tag.

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

**50% complete.** Market context now has a strict evidence boundary: timestamped source records, primary-source priority, bounded/fresh context, post-cutoff rejection and a hashed audit manifest. Next block is **50% → 55%: Deterministic evaluator**.
