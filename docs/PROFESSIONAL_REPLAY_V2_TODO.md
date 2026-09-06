# Professional Replay v2 — TODO

Status: IN PROGRESS

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
- [ ] Pull ~2 years of daily OHLCV for the entire frozen universe plus SPY.
- [ ] Compute multi-horizon technical context from the complete available history at cutoff.
- [ ] Include trend, volatility, drawdown, relative strength, volume behaviour, SMA20/50/200 and support/resistance candidates.
- [ ] Preserve raw OHLCV for the selected asset so the chart can reproduce what the model saw.

Acceptance: every replay contains a complete cutoff-safe market context, not merely 20 recent closes.

## 20–30% — Historical news/evidence reconstruction
- [ ] Pull historical news available no later than cutoff.
- [ ] Attach publication timestamp, source, headline, summary and URL.
- [ ] Enforce cutoff validation before any article can reach the model.
- [ ] Keep a replay evidence manifest for auditability.

Acceptance: the model can explain which historical news it used, with clickable sources, without future leakage.

## 30–40% — Explicit market-selection stage
- [ ] Add a separate AI market scan over the complete allowed universe.
- [ ] Rank/compare candidates and allow `NO_TRADE` when nothing is compelling.
- [ ] Record why the selected asset was preferred to alternatives.
- [ ] Keep this selection logically separate from capital sizing.

Acceptance: the replay can answer “why this stock today?” before deciding what to do with money.

## 40–50% — Professional decision + pedagogical explanation
- [ ] Generate a short decision card (action, symbol, amount, confidence, horizon, stop/target).
- [ ] Generate a long pedagogical explanation below it.
- [ ] Explain chart reading: timeframe, candles, trend, levels, volume, volatility and invalidation.
- [ ] Link every news/evidence item actually used.
- [ ] Expose assumptions and counter-thesis.

Acceptance: a non-trader can understand the decision and inspect the evidence used to make it.

## 50–60% — Position lifecycle / day-by-day re-evaluation
- [ ] Re-run the thesis sequentially using only information available on each subsequent historical day.
- [ ] Produce a table: date → new information → current thesis → BUY/HOLD/SELL/NO_TRADE.
- [ ] Stop the simulated position when the model recommends SELL or the frozen horizon/stop rule closes it.
- [ ] Measure P/L from the actual simulated entry to the model-selected exit.

Acceptance: replay tests management of the position, not only next-day direction.

## 60–70% — Reveal and counterfactual evaluator
- [ ] Hide all post-cutoff bars until the reveal step.
- [ ] Reveal actual future candles on demand.
- [ ] Show realized simulated P/L when following the AI literally.
- [ ] Compare with SPY and with post-exit continuation, clearly labelled as hindsight-only diagnostics.
- [ ] Show whether the AI exited too early/late without feeding this information back into the earlier decision.

Acceptance: the page distinguishes prospective reasoning from hindsight diagnostics.

## 70–80% — Professional embedded charts
- [ ] Replace the simple replay line plot with interactive candlestick charts.
- [ ] Add volume and viewport buttons `1W / 1M / 3M / 1Y / 2Y`.
- [ ] Show SMA20/50/200 when relevant.
- [ ] Overlay support/resistance, entry, stop, target and exit markers.
- [ ] Make post-cutoff candles visually distinct only after reveal.

Acceptance: charts resemble a real market-analysis workstation and are generated from the same source data used by the model.

## 80–90% — UX decision room
- [ ] Keep a prominent `Replay histórico ↔ En vivo` mode switch.
- [ ] Add explicit stage buttons: `Explorar mercado`, `Consultar a ChatGPT`, `Aplicar sugerencia`, `Avanzar/Reevaluar`, `Ver qué pasó después`.
- [ ] Progressive disclosure: short answer first, detailed lesson below.
- [ ] Show “what ChatGPT analysed” separately from “what you are viewing”.
- [ ] Make mobile interaction usable.

Acceptance: a user can learn the workflow without reading documentation.

## 90–100% — Safety, tests, deploy and handoff
- [ ] Add tests for cutoff leakage, replay/forward isolation, technical context and lifecycle evaluation.
- [ ] Add public-data safety scan for replay artifacts.
- [ ] Ensure GitHub Pages deploy includes replay v2 artifacts.
- [ ] Run the complete acceptance suite.
- [ ] Verify the public page and mark this TODO complete.

Acceptance: CI + Pages are green and the professional replay is usable without touching the forward cohort.

## Definition of done

The page lets a user replay a past market day without future leakage, watch the AI choose where to focus, understand the chart/news reasoning, apply the suggestion, re-evaluate it day by day, reveal what actually happened, and compare the outcome — while the official live cohort remains untouched.
