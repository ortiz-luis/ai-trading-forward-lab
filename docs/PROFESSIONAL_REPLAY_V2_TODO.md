# Professional Replay v2 — TODO

Status: 95% — IMPLEMENTED, FINAL PUBLIC VERIFICATION PENDING

Goal: turn the current blind replay prototype into a professional, pedagogical decision room while keeping the official forward cohort isolated and immutable.

## Non-negotiable invariants

- Replay data never writes to `data/decisions.jsonl`, `data/evaluations.jsonl`, or `data/cohort_v1.json`.
- Historical replay calls may use only information with timestamps at or before their cutoff.
- The UI viewport never limits what the analysis engine is allowed to inspect.
- The official forward cohort keeps its frozen protocol and ledger semantics.
- Simulation only; no real-money credentials or broker writes.

## 0–10% — Freeze the v2 product contract
- [x] Write this versioned TODO.
- [x] Define Replay vs Live separation.
- [x] Define staged UX: Explore → Choose → Decide → Apply → Follow → Reveal.
- [x] Define expert chart requirement: candlesticks + volume + multi-horizon context.

Acceptance: the intended user journey and isolation rules are explicit in GitHub.

## 10–20% — Professional historical context engine
- [x] Pull ~2 years of daily OHLCV for the entire frozen universe plus SPY.
- [x] Compute multi-horizon technical context from the complete available history at cutoff.
- [x] Include trend, volatility, drawdown, relative strength, volume behaviour, SMA20/50/200 and support/resistance candidates.
- [x] Preserve raw OHLCV for the selected asset so the chart can reproduce what the model saw.

Acceptance: every replay contains a complete cutoff-safe market context, not merely 20 recent closes.

## 20–30% — Historical news/evidence reconstruction
- [x] Pull historical news available no later than cutoff.
- [x] Attach publication timestamp, source, headline, summary and URL.
- [x] Enforce cutoff validation before any article can reach the model.
- [x] Keep replay evidence in the auditable replay artifact.

Acceptance: the model can explain which historical news it used, with clickable sources, without future leakage.

## 30–40% — Explicit market-selection stage
- [x] Add a separate AI market scan over the complete allowed universe.
- [x] Rank/compare candidates and allow `NO_TRADE` when nothing is compelling.
- [x] Record why the selected asset was preferred to alternatives.
- [x] Keep this selection logically separate from capital sizing.

Acceptance: the replay can answer “why this stock today?” before deciding what to do with money.

## 40–50% — Professional decision + pedagogical explanation
- [x] Generate a short decision card (action, symbol, amount, confidence, horizon, stop/target).
- [x] Generate a long pedagogical explanation below it.
- [x] Explain chart reading: timeframe, candles, trend, levels, volume, volatility and invalidation.
- [x] Link every cutoff-safe news/evidence item exposed for inspection.
- [x] Expose assumptions and counter-thesis.

Acceptance: a non-trader can understand the decision and inspect the evidence used to make it.

## 50–60% — Position lifecycle / day-by-day re-evaluation
- [x] Re-run the thesis sequentially using only information available on each subsequent historical day.
- [x] Produce a table: date → new information → current thesis → HOLD/SELL.
- [x] Stop the simulated position when the model recommends SELL or the frozen horizon closes it.
- [x] Measure P/L from the actual simulated entry to the model-selected exit.

Acceptance: replay tests management of the position, not only next-day direction. Verified with MA multi-day HOLD and V HOLD→SELL examples.

## 60–70% — Reveal and counterfactual evaluator
- [x] Hide all post-cutoff bars until the reveal step.
- [x] Reveal actual future candles on demand.
- [x] Show realized simulated P/L when following the AI literally.
- [x] Compare with SPY and with post-exit continuation, clearly labelled as hindsight-only diagnostics.
- [x] Show post-exit price continuation without feeding it back into the earlier decision.

Acceptance: the page distinguishes prospective reasoning from hindsight diagnostics.

## 70–80% — Professional embedded charts
- [x] Replace the simple replay line plot with interactive candlestick charts.
- [x] Add volume and viewport buttons `1W / 1M / 3M / 1Y / 2Y`.
- [x] Show SMA20/50/200 for orientation.
- [x] Overlay support/resistance, entry, target and exit/cutoff markers when applicable.
- [x] Keep post-cutoff candles absent until reveal.

Acceptance: charts are generated from the same OHLCV source data used by the model and use a dedicated financial-chart renderer.

## 80–90% — UX decision room
- [x] Keep a prominent `Replay histórico ↔ En vivo` mode switch.
- [x] Add explicit stage buttons: `Explorar mercado`, `Consultar a ChatGPT`, `Aplicar sugerencia`, `Avanzar un día`, `Ver qué pasó después`.
- [x] Progressive disclosure: short answer first, detailed lesson below.
- [x] Show “what ChatGPT analysed” separately from “what you are viewing”.
- [x] Add responsive mobile layout.

Acceptance: a user can learn the workflow without reading documentation.

## 90–100% — Safety, tests, deploy and handoff
- [x] Add tests for cutoff leakage, replay/forward isolation, technical context and result/lifecycle evaluation.
- [x] Add public-data safety scan and structural validation for replay artifacts.
- [x] Ensure GitHub Pages workflow includes replay v2 artifacts.
- [x] Run the complete acceptance suite and professional replay generation workflow successfully.
- [ ] Verify the newly published public page end-to-end and mark this TODO complete.

Acceptance: CI + Pages are green and the professional replay is usable without touching the forward cohort.

## Verified implementation evidence

- Professional generation created 3 blind sessions with `forward_ledger_untouched=true`.
- Artifact validation passed before persistence.
- At least two sessions are actionable BUY examples after correcting support/resistance to use prior-session levels.
- MA example: BUY, followed by sequential HOLD assessments through the horizon.
- V example: BUY, HOLD, then SELL when the predefined breakout thesis was invalidated.
- Forward cohort files remained unchanged during generation.

## Definition of done

The page lets a user replay a past market day without future leakage, watch the AI choose where to focus, understand the chart/news reasoning, apply the suggestion, re-evaluate it day by day, reveal what actually happened, and compare the outcome — while the official live cohort remains untouched.
