# AI Trading Forward Lab

GitHub-first, forward-only experiment for observing how an AI manages a **simulated** portfolio over time.

> **Current progress: 70% / 100%**  
> **Current gate: STOP — waiting for explicit `sigue` before starting 80%.**

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
- Work advances in exact **10% gates** and stops until the user says `sigue`.

# Master implementation plan — 0% → 100%

A block is complete only when its acceptance criteria pass.

## 0% → 10% — Architecture + executable skeleton ✅
- [x] Public repository and README master board.
- [x] Pages + Actions + Python + OpenAI API + market adapter + append-only ledger architecture.
- [x] Simulation-only boundary.
- [x] Python 3.11+ package, deterministic config, offline CLI and smoke tests.

## 10% → 20% — Immutable events + portfolio accounting ✅
- [x] Strict decision/evaluation/system schemas, UTC timestamps, deterministic IDs/idempotency, JSONL ledger and SHA-256 locked decisions.
- [x] €1,000 configurable start, cash/equity/positions/P&L fields, BUY/HOLD/SELL/NO_TRADE transitions, exposure guards and ledger replay.

## 20% → 30% — Market data architecture + Alpaca adapter ✅
- [x] Provider contract, deterministic fixture, quote/candle models, audit snapshots and fail-closed stale/missing/closed handling.
- [x] Alpaca Market Data adapter with environment-only credentials, quote/bar normalization, retries, health state and safe probe.

## 30% → 40% — Frozen trading protocol + OpenAI decision contract ✅
- [x] Liquid US-equity universe; SPY benchmark.
- [x] Long-only, no leverage/short/options/futures/CFDs/crypto.
- [x] Max 3 positions, 15% per position, 45% total exposure.
- [x] Stop bounds -1% to -5%, horizon 2–10 trading days, forward-only entry and explicit `NO_TRADE` rules.
- [x] Versioned prompt, strict Structured Output schema and cutoff-aware input.
- [x] Output requires simulated decision, confidence, horizon, stop, thesis/counter-thesis and sources.

## 40% → 50% — OpenAI API + evidence boundary ✅
- [x] Official OpenAI SDK / Responses API behind `OpenAIDecisionProvider`.
- [x] `OPENAI_API_KEY` only from runtime environment/GitHub Secret.
- [x] Strict JSON schema, bounded timeout/retries and one repair attempt.
- [x] Explicit `AI_ERROR`; failure never becomes `NO_TRADE`.
- [x] Timestamped evidence records with primary-source priority.
- [x] Bounded context, freshness rules, post-cutoff rejection and hashed evidence manifest.

## 50% → 60% — Deterministic evaluator + experiment statistics ✅
- [x] Forward-only entry, stop, horizon and explicit SELL semantics.
- [x] Configurable simulated transaction costs/slippage.
- [x] Gross/net P&L and same-window SPY benchmark.
- [x] Evaluation events never alter locked decisions.
- [x] Wins/losses/breakeven/NO_TRADE/errors tracked separately.
- [x] Reproducible equity, drawdown, benchmark, game score and confidence calibration.
- [x] Acceptance fixtures for win/loss/stop/SELL/costs/benchmark/drawdown/calibration.

## 60% → 70% — GitHub Actions automation + resilience ✅
- [x] Daily scheduled decision workflow at 16:17 Europe/Paris, Monday–Friday.
- [x] Authenticated manual `workflow_dispatch` on decision and evaluation workflows.
- [x] Periodic evaluation workflow at minute 47 each hour, Monday–Friday.
- [x] Shared `ai-trading-state` concurrency group prevents simultaneous state writes.
- [x] Date/protocol idempotency prevents duplicate same-session decisions.
- [x] Controlled sanitized-context → OpenAI → strict validation → immutable decision persistence adapter.
- [x] Controlled evaluation-input → deterministic evaluator → append-only evaluation persistence adapter.
- [x] Test suite runs before and after scheduled cycles.
- [x] Runtime credentials are supplied only through GitHub Secrets/environment.
- [x] Only sanitized `data/` state is committed; workflows rebase before push.
- [x] Explicit `DATA_ERROR`, `AI_ERROR`, `DEPLOY_ERROR` event infrastructure and `health.json`.
- [x] Prior successful timestamps remain intact after later failures.
- [x] Synthetic tests cover same-session idempotency, missing secrets, repeated evaluation, health-state persistence and multi-day injected failures.
- [x] Package discovery corrected so `engine.*` subpackages install consistently in fresh Actions environments.
- [x] Automation/failure semantics documented in `docs/AUTOMATION_AND_RESILIENCE.md`.

**Acceptance:** the unattended control plane is deterministic and fail-closed: repeated same-session runs cannot duplicate a decision; failures are recorded explicitly instead of fabricating a trade; decision/evaluation state writes are serialized. The official forward cohort has not started yet. Until later gates generate the finalized runtime context and public artifacts, automation is allowed to stop safely rather than create unauditable data. Pages deployment remains separate so a future deployment failure cannot rewrite ledger history.

## 70% → 80% — Public-data layer + beginner-first UI
- [ ] Sanitized dashboard JSON; no secret/environment serialization.
- [ ] “Mientras no estuviste”, current portfolio, equity series and latest cards.
- [ ] Secret-pattern scan of publishable artifacts.
- [ ] Responsive home page.
- [ ] Hero: starting money → current money → gain/loss.
- [ ] Simple latest decision, positions, green/red/neutral history and cumulative equity chart.

**Acceptance:** public artifacts contain everything the UI needs and nothing secret; a first-time user understands the experiment in under 10 seconds.

## 80% → 90% — Pages deployment + optional Alpaca Paper shadow
- [ ] Official Pages deployment and correct project base path.
- [ ] Authorized manual “request a decision now”.
- [ ] Health/update status, mobile/desktop and HTTPS validation.
- [ ] Optional Alpaca paper-only broker adapter.
- [ ] Mirror eligible simulated decisions and reconcile paper fills.
- [ ] Never overwrite internal ledger; hard-block live endpoint/credentials.

**Acceptance:** public site works without exposing credentials; Alpaca Paper can be disabled entirely and internal truth remains reproducible.

## 90% → 100% — Hardening, freeze and forward cohort v1
- [ ] Secret scan, failure injection, rebuild-from-zero and duplicate schedule test.
- [ ] Dependency/recovery policy.
- [ ] Freeze cohort prompt/protocol/provider/model/evidence settings and create checkpoint tag.
- [ ] Initialize official simulated €1,000 cohort.
- [ ] Generate observation #1 prospectively and verify timestamp/evidence/hash/UI.
- [ ] Verify unattended evaluator and document frozen start configuration.

**Acceptance:** the experiment can run for days without the user and honestly answer what ChatGPT would have done and how much simulated money would remain.

# Future gate: real money — outside this 0–100 plan

No automatic promotion to live trading. A separate design review is required after a sufficiently informative forward-simulation cohort.

## Working protocol for future chats

1. Read README and current repo state.
2. Identify completed percentage.
3. Execute only the next **10% block**.
4. Run/add its acceptance checks.
5. Update README and mark only genuinely completed items.
6. Commit checkpoint.
7. **STOP** until the user says `sigue`.

## Current checkpoint

**70% complete.** The project now has a scheduled, manual-triggerable, serialized and fail-closed automation layer for simulated decisions and evaluations, plus explicit health/error state and idempotency. Next block is **70% → 80%: Public-data layer + beginner-first UI**.
