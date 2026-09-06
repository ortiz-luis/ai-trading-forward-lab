# Automation and resilience — 60% to 70%

## Purpose

This gate establishes the unattended control plane without starting the official forward cohort yet.

## Scheduled decision cycle

`.github/workflows/daily-decision.yml`

- Runs Monday–Friday at 16:17 Europe/Paris.
- Can also be started manually with `workflow_dispatch`.
- Uses one shared concurrency group (`ai-trading-state`) so decision and evaluation workflows cannot write repository state simultaneously.
- Runs the full test suite before and after the cycle.
- Receives OpenAI and Alpaca credentials only through GitHub Secrets/runtime environment.
- Persists only changed files under `data/`.
- Uses rebase-before-push to reduce commit races.

The runner checks date/protocol idempotency before a new decision can exist. A second run for the same session must not create another decision.

## Periodic evaluation cycle

`.github/workflows/evaluate.yml`

- Runs at minute 47 of each hour Monday–Friday, Europe/Paris.
- Can be invoked manually.
- Shares the same concurrency lock.
- Is safe when there is nothing to evaluate.

## Fail-closed state

`engine/automation.py` provides:

- `health.json` read/write helpers;
- explicit `DATA_ERROR`, `AI_ERROR`, `DEPLOY_ERROR` event recording;
- preservation of the previous successful decision/evaluation timestamps when a later cycle fails;
- guarded boundaries that convert exceptions into auditable state rather than fabricated decisions.

External-data or AI failures are never converted into `NO_TRADE`.

## Current production boundary

The scheduled infrastructure is active in code, but the official forward cohort has **not** started. Until the remaining gates wire the publishable data layer/UI and freeze the cohort, the runner may intentionally fail closed rather than create an unauditable decision. That is expected behavior, not a fallback trade.

## Pages failure semantics

Pages deployment itself belongs to the later Pages gate. The rule is already fixed: deployment must be separate from state persistence so a failed site build cannot delete or rewrite ledger state; the previously deployed site remains the last known good public view.

## Acceptance tests

`tests/test_automation.py` covers:

- same-session idempotency;
- health-state round trip;
- explicit error conversion;
- preservation of prior successful timestamps;
- synthetic multi-day `DATA_ERROR` / `AI_ERROR` / `DEPLOY_ERROR` sequences without state corruption.
