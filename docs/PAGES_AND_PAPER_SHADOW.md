# GitHub Pages and optional Alpaca Paper shadow

## GitHub Pages

The public dashboard is deployed by `.github/workflows/pages.yml` using the official GitHub Pages workflow path:

1. checkout
2. install package + tests
3. regenerate sanitized `dashboard.json`
4. assemble `_site/`
5. `actions/configure-pages@v5`
6. `actions/upload-pages-artifact@v4`
7. `actions/deploy-pages@v4`

The site is assembled so that `index.html`, `styles.css`, `app.js`, and `data/dashboard.json` all live under the project Pages root. The browser therefore uses a relative `./data/dashboard.json` path and does not depend on a custom domain or repository-root URL.

The dashboard exposes a link to the authenticated GitHub Actions page for `daily-decision.yml`. This is intentionally not a browser-side API endpoint: only a logged-in GitHub user with repository permissions can manually dispatch the workflow and spend API budget.

## Health and mobile behavior

The public payload exposes only the approved health summary. The UI shows the current simulation status plus the last safe update when available. CSS collapses the three-column hero, four-stat row, two-column content section and advanced metrics to one column below 760 px.

## Alpaca Paper shadow

`engine/providers/alpaca_paper.py` is optional and never becomes accounting truth.

Safety rules:

- hard-coded base URL: `https://paper-api.alpaca.markets`
- `https://api.alpaca.markets` and every other base URL are rejected at construction time
- credentials are read only from `ALPACA_PAPER_API_KEY` / `ALPACA_PAPER_API_SECRET`
- `NO_TRADE` and `HOLD` create no paper request
- BUY uses a stable `client_order_id` derived from the immutable decision id
- SELL mirrors the v1 full-close semantics by closing the paper position
- `reconcile_order()` can inspect a paper order without altering the internal ledger
- paper fills are comparison/shadow metadata only; they never overwrite decisions, evaluation events or portfolio state

Paper shadow remains disabled unless its separate credentials are deliberately supplied. No live brokerage credential or endpoint is accepted by the adapter.

## Verification boundary

Repository tests cover live-endpoint blocking, paper-only configuration, no-request behavior for HOLD/NO_TRADE, BUY client-order idempotency and SELL full-close mirroring. Live Pages/HTTPS and paper-account network verification require external connectivity and credentials; those are final hardening checks before the official forward cohort starts.
