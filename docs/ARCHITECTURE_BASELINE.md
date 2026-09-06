# Architecture Baseline — v1

This document freezes the architectural direction for the first simulation-only cohort.

## Goal

Run a forward-only AI trading experiment that can continue unattended and later answer, audibly and reproducibly: **what did the AI decide with the information available at the time, and how much simulated money would the portfolio have now?**

## Frozen v1 architecture

- **Public UI:** GitHub Pages.
- **Automation:** GitHub Actions scheduled workflows plus authorized manual dispatch.
- **Core logic:** deterministic Python package.
- **AI:** OpenAI API invoked only from Actions/runtime code, never directly from browser JavaScript.
- **Market information:** provider behind an adapter interface so it can be replaced without rewriting the engine.
- **State/audit:** append-only event ledger committed to Git plus derived public JSON for the UI.
- **Optional execution cross-check:** paper broker adapter, initially Alpaca Paper candidate; never a live account in phase 1.

## Security boundary

The browser receives no API secrets. OpenAI and market-provider keys live only in GitHub Actions Secrets/runtime environment. Published artifacts are sanitized and scanned before deployment.

## Scientific boundary

- Forward-only decisions.
- Decision payload frozen before outcome.
- AI chooses among allowed actions; code performs accounting.
- Errors are explicit events, never silently converted to NO_TRADE.
- Prompt/protocol changes create a new cohort/version; prior observations remain untouched.

## UX boundary

The default view remains beginner-first:

1. starting simulated money,
2. simulated money now,
3. cumulative gain/loss,
4. what ChatGPT did recently,
5. what happened while the user was away.

Advanced metrics are secondary.

## Out of scope for v1

- Real-money orders.
- Live broker credentials.
- Leverage, options, short selling, or low-latency intraday trading.
- Multi-user authentication.
- A permanent backend server.
- Automatic prompt optimization against already observed outcomes.

## Working cadence

Implementation advances exactly 5 percentage points at a time. Each gate is validated and committed, then work stops until the user explicitly says `sigue`.
