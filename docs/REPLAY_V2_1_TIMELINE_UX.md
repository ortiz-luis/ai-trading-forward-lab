# Replay v2.1 — Timeline-first UX

Status: 100% — COMPLETE

## Product change

The chart becomes the primary narrative surface. Text is secondary.

A replay starts at the historical cutoff. Everything to the left is information ChatGPT could see. Nothing to the right is visible yet. The user then advances simulated time and reveals one new market session at a time.

## Timeline interaction

1. At cutoff, show the historical candlestick chart and the initial ChatGPT thesis.
2. `+1 día` reveals exactly one subsequent completed market session.
3. After each revealed session, show ChatGPT's updated position assessment on the same timeline.
4. `+1 semana` reveals up to five sessions and `+1 mes` up to 22 sessions.
5. The chart never jumps ahead merely because future data exists in the replay artifact.

## Sell-confidence track

The right vertical axis is a 0–100% exit-confidence scale.

- One point is plotted at cutoff from the initial BUY confidence.
- One point is added for every ChatGPT reassessment that has become visible in simulated time.
- Points are connected so changes of mind are visible without reading a table.
- Default sell threshold: 80%.
- The first visible point crossing the threshold marks the simulated sale.
- Before the crossing, the UI is in `GESTIÓN DE LA POSICIÓN` mode.
- At and after the crossing, the UI changes automatically to `ANÁLISIS RETROSPECTIVO` mode.

For the current v2 artifact, sell confidence is derived losslessly from the model's daily structured assessment: `SELL → confidence`, `HOLD → 1 - confidence`. Initial sell confidence is `1 - BUY confidence`. This keeps the historical model calls unchanged and does not contaminate the existing replay corpus.

## Chart layers

Primary market axis:
- candlesticks
- volume
- SMA/levels when useful
- cutoff marker
- entry marker
- sale marker
- current simulated-day marker

Secondary right axis:
- ChatGPT sell-confidence line, constrained to 0–100%
- horizontal 80% threshold
- current sell-confidence value

## Two phases

### Phase A — prospective management
Only data revealed up to the current simulated day is shown. The user watches ChatGPT update its view without knowing later prices.

### Phase B — hindsight audit
Begins after the threshold-triggered sale, or after a protocol horizon exit when no threshold crossing occurs. The user can continue `+1 día`, `+1 semana`, or `+1 mes` and visually judge whether the sale was early, late, or sensible. Later information never changes the historical sale decision.

## Acceptance criteria — verified

- [x] One chart carries the story from cutoff through hindsight.
- [x] No future candle appears before the user advances time.
- [x] Sell confidence is plotted on a right-side 0–100% axis.
- [x] An 80% threshold is visible.
- [x] The first threshold crossing identifies the simulated sale.
- [x] `+1 día`, `+1 semana`, and `+1 mes` controls exist.
- [x] After sale, advancing time becomes retrospective analysis.
- [x] Existing lifecycle details remain available in a compact table.
- [x] Forward cohort files remain untouched.
- [x] Full acceptance tests passed.
- [x] GitHub Pages build completed successfully.
- [x] GitHub Pages deployment completed successfully.

## Implementation

- `app/index.html`: timeline-first controls and wording.
- `app/app.js`: progressive future reveal, sell-confidence conversion, secondary-axis series, 80% threshold, automatic phase transition, and multi-speed time advancement.
- `app/styles.css`: timeline controls and responsive layout.

GitHub Pages run `34062096433` completed with both build and deploy jobs successful.
