# Professional Replay v2 — UI/UX review

## Product question

How can a non-professional trader learn from an AI trading process without turning the page into an overloaded terminal, while preserving the scientific blind-replay contract?

## Main finding

The page should not expose every dataset at once. It should expose the **same analytical workflow in the same order the AI uses it**:

1. Explore the allowed market universe.
2. Choose where to focus.
3. Inspect the chosen chart and evidence.
4. Make a concise decision.
5. Expand the pedagogical reasoning.
6. Apply the suggestion in simulation.
7. Re-evaluate with each new day of information.
8. Reveal the future only after the user explicitly asks.

This progressive disclosure reduces cognitive load and makes Replay an educational simulation of the future Live workflow rather than a separate toy.

## Information hierarchy

### Level 1 — answer first
The most visible card must answer in seconds:
- selected asset or NO_TRADE;
- BUY / HOLD / SELL / NO_TRADE;
- amount;
- confidence;
- expected horizon;
- stop / target when applicable.

### Level 2 — teach the reasoning
Directly below, explain:
- why this asset beat the alternatives;
- what the candles and volume mean;
- which time horizons mattered;
- which news items materially changed the thesis;
- what would invalidate the idea.

### Level 3 — auditability
Expose:
- source links and publication times;
- cutoff timestamp;
- analysed-history scope;
- day-by-day thesis evolution;
- hindsight-only diagnostics after reveal.

## Chart recommendation

Use a dedicated financial chart renderer rather than screenshots or arbitrary embedded third-party pages. The chart should be recreated from the exact OHLCV data supplied to the analytical engine.

Default viewport: **1M**.
Available viewports: **1W / 1M / 3M / 1Y / 2Y**.

The selected viewport is only the user's camera. It must never truncate the model's analysis context.

Chart elements:
- candlesticks;
- volume;
- SMA20 / SMA50 / SMA200 for orientation;
- support/resistance levels that existed before the current candle;
- target / entry / exit markers when applicable;
- cutoff marker;
- post-cutoff candles hidden until reveal.

## Interaction review

Recommended primary buttons, in order:

`Explorar mercado` → `Consultar a ChatGPT` → `Aplicar sugerencia` → `Avanzar un día` → `Ver qué pasó después`

Each button unlocks one new information layer. This makes future leakage visually difficult as well as technically impossible.

## Replay vs Live

Use one prominent two-state mode switch:

`Replay histórico ↔ En vivo`

The mental model should remain identical. Replay has an artificial clock that the user can advance. Live does not.

Replay state must never affect forward statistics or portfolio state.

## Mobile

On narrow screens:
- stages stack vertically;
- the chart remains full width;
- viewport controls wrap;
- evidence becomes a vertical list;
- the long lesson follows the short answer rather than competing with it.

## Anti-patterns to avoid

- Showing all 18 stock charts at once.
- Treating RSI/MACD/etc. as decoration when they did not influence the decision.
- Showing future candles faintly before reveal.
- Mixing historical Replay P/L with forward cohort P/L.
- Using screenshots when underlying OHLCV can be rendered interactively.
- Hiding the cutoff or source timestamps.

## Acceptance criteria

A first-time user should be able to answer, without reading project documentation:

1. What did ChatGPT inspect?
2. Why did it choose this asset?
3. What does it want to do?
4. How much fictitious capital does it want to use?
5. What does it see in the chart?
6. Which news/evidence mattered?
7. When would it change its mind?
8. What happened after the decision?
9. Did following it literally make or lose money?
10. Which information shown after reveal was hindsight-only?
