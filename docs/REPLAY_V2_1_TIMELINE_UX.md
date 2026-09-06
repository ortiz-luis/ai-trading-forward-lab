# Replay v2.1 — Timeline-first UX

Status: IMPLEMENTATION IN PROGRESS

## Product change

The chart becomes the primary narrative surface. Text is secondary.

A replay starts at the historical cutoff. Everything to the left is information ChatGPT could see. Nothing to the right is visible yet. The user then advances simulated time and reveals one new market session at a time.

## Timeline interaction

1. At cutoff, show the historical candlestick chart and the initial ChatGPT thesis.
2. `+1 día` reveals exactly one subsequent completed market session.
3. After each revealed session, show ChatGPT's updated position assessment on the same timeline.
4. Also provide `+1 semana` and `+1 mes` controls for faster hindsight exploration.
5. The chart must never jump ahead merely because future data exists in the replay artifact.

## Sell-confidence track

The right vertical axis is a 0–100% exit-confidence scale.

- Plot one point per ChatGPT reassessment.
- Connect points as a line so changes of mind are visible without reading a table.
- Default sell threshold: 80%.
- The first point crossing the threshold marks the simulated sale.
- Before the crossing, the UI is in `GESTIÓN DE LA POSICIÓN` mode.
- At and after the crossing, the UI changes to `ANÁLISIS RETROSPECTIVO` mode.

For the current v2 artifact, sell confidence is derived losslessly from the model's daily structured assessment: `SELL → confidence`, `HOLD → 1 - confidence`. A later schema revision may expose `sell_confidence` directly, but the public UX does not need to wait for regeneration.

## Chart layers

Primary left axis:
- candlesticks
- volume
- SMA/levels when useful
- entry marker
- sale marker

Secondary right axis:
- ChatGPT sell-confidence line, 0–100%
- horizontal 80% threshold
- point labels/tooltips for each reassessment

## Two phases

### Phase A — prospective management
Only data revealed up to the current simulated day is shown. The user watches ChatGPT update its view without knowing later prices.

### Phase B — hindsight audit
Begins after the threshold-triggered sale. The user can continue `+1 día`, `+1 semana`, or `+1 mes` and visually judge whether the sale was early, late, or sensible. No later information is allowed to alter the historical sale decision.

## Acceptance criteria

- One chart carries the complete story from cutoff through hindsight.
- No future candle appears before the user advances time.
- Sell confidence is plotted on a right-side 0–100% axis.
- An 80% threshold is visible.
- The first threshold crossing identifies the sale.
- `+1 día`, `+1 semana`, and `+1 mes` advance controls exist.
- After sale, advancing time continues only for retrospective analysis.
- Forward cohort files remain untouched.
