# Forward cohort v1 — freeze, start and recovery

## Current state

`data/cohort_v1.json` is the authoritative cohort control file.

Before the first prospective observation it must remain:

- cohort: `forward-v1`
- status: `ARMED_NOT_STARTED`
- starting simulated capital: EUR 1,000
- observation count: 0
- real money: EUR 0

The scheduled decision runner does nothing while the cohort is armed. Only the authenticated `Start official forward cohort v1` GitHub Actions workflow can perform the one-way start transition.

## Frozen v1 experiment

The freeze file records the exact model, prompt/protocol versions and Git blob SHAs for the core scientific components. v1 also freezes:

- Python 3.11
- OpenAI Python SDK 3.8.0
- pytest 9.1.1 for acceptance verification
- Alpaca Market Data as the market source
- `gpt-5.6-terra` as the model identifier
- Europe/Paris decision schedule at 16:17 Monday–Friday
- maximum 12 evidence records; primary <=168 h; secondary <=72 h
- EUR 1,000 simulated starting capital

Any scientific change after observation #1 requires a new cohort version. Historical v1 decisions/evaluations are never rewritten.

## Secrets required for the official start

Create these repository Actions secrets before running the start workflow:

- `OPENAI_API_KEY`
- `ALPACA_API_KEY`
- `ALPACA_API_SECRET`

The workflows map the Alpaca secrets to the environment names used by both the market-data and control layers. Secrets must never be committed to the repository or dashboard.

## Official start sequence

The authenticated workflow `.github/workflows/start-cohort.yml` performs the complete start atomically from a clean checkout:

1. run the full acceptance suite;
2. obtain fresh Alpaca quotes/candles and create a new cutoff-aware runtime context;
3. write its evidence manifest/hash;
4. verify the cohort is still armed, history is empty and required secrets exist;
5. transition the cohort to `STARTED`;
6. request exactly one structured OpenAI decision;
7. validate sources, current portfolio constraints and protocol bounds;
8. append and hash the decision;
9. increment observation count to 1;
10. rebuild the sanitized public dashboard;
11. assert exactly one locked decision exists;
12. rerun all acceptance tests;
13. commit only the resulting `data/` state.

If any step before the final git commit fails, the runner filesystem is discarded and the repository remains `ARMED_NOT_STARTED`. The workflow can therefore be retried without manufacturing a partial official start.

## Daily unattended behavior after start

Decision workflow:

- builds a fresh market context every scheduled session;
- rejects closed/stale/missing market data;
- calls OpenAI only after the cohort is `STARTED`;
- validates evidence references and current effective portfolio constraints before append;
- same-session idempotency prevents duplicates;
- rebuilds the public dashboard after a successful cycle.

Evaluation workflow:

- scans unevaluated BUY decisions;
- retrieves recent Alpaca candle history;
- closes at the first eligible stop, explicit SELL, or frozen horizon;
- aligns SPY to the same timestamps;
- appends one deterministic evaluation per BUY;
- rebuilds the dashboard;
- later decision contexts reconcile those evaluation results so closed positions do not remain open.

## Recovery policy

### Code or deployment failure

Do not edit ledger history. Fix/revert code and rerun tests/deployment. `decisions.jsonl` and `evaluations.jsonl` remain authoritative.

### Decision provider or market-data failure

Record explicit failure state and make no decision. A provider error is never converted into `NO_TRADE`.

### Git push conflict

Workflows use a shared concurrency group and rebase before push. If persistence still fails, the next run reads only committed state; no uncommitted runner state is treated as history.

### Rebuild from zero

The public dashboard and effective portfolio can be reconstructed from committed decision/evaluation ledgers plus the frozen cohort configuration. Generated public files are disposable derivatives.

### Secret rotation

Replace the repository secret in GitHub Settings. No historical artifact needs editing because secret values are never persisted.

### Model/provider/protocol change

Do not modify v1 after observation #1. Create v2 with a new cohort ID, freeze file and start boundary.

## Pages prerequisite

The repository must have GitHub Pages configured for GitHub Actions. The Pages workflow requests enablement through `actions/configure-pages@v5`; if GitHub account/repository policy prevents automatic enablement, enable it once under **Settings -> Pages -> Build and deployment -> Source: GitHub Actions** and rerun `Deploy public dashboard`.
