# Replay vs Live UI/UX contract

## Goal

Let a beginner learn the exact interaction model before the forward cohort starts, without contaminating the forward ledger or leaking future information into a historical replay.

## Two explicit modes

The page exposes two strongly signaled modes:

- **Replay histórico** — retrospective laboratory mode using blind, time-frozen inputs.
- **En vivo** — prospective forward cohort using only information available in the current valid market session.

Mode state must always be visually obvious. Replay data never counts toward forward statistics.

## Replay progressive-disclosure flow

1. **Choose a replay date** and inspect the chart that was available at the cutoff.
2. **Consultar a ChatGPT** reveals the already-sealed blind answer.
3. **Aplicar sugerencia** advances only to the next eligible market open and reveals the simulated entry.
4. **Ver qué pasó después** reveals the subsequent outcome and P/L.

No post-cutoff price is rendered before the corresponding reveal step.

## Chart design

- Default context window: **1 month**.
- Optional compact context: **1 week**.
- The selected asset can be changed; SPY is available as benchmark context.
- The chart is explicitly labeled as what ChatGPT could see at the cutoff.
- Future points, once deliberately revealed, are visually distinct from pre-cutoff context.

## Security and data integrity

- Replay artifacts live under `data/replay/`.
- Replay generation is server-side in GitHub Actions with Secrets.
- The public page never receives API credentials.
- Replay generation is guarded against changes to `data/decisions.jsonl`, `data/evaluations.jsonl`, or `data/cohort_v1.json`.
- The live public page does not call OpenAI directly from JavaScript. Until an authenticated backend exists, manual live requests remain behind GitHub Actions authentication.

## Current replay scope

Replay decisions are grounded in historical Alpaca OHLCV market context and the frozen trading protocol. Historical news reconstruction is not yet included, so the UI must not imply that the replay model saw a complete historical news feed.
