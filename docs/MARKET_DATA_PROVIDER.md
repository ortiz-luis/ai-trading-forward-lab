# Market data provider decision — v1

## Selected first external provider

**Alpaca Market Data API** is the first real provider to implement in the 25% → 30% gate.

Reasons:

- official REST endpoints for latest stock quotes and minute bars;
- historical bars and quotes available through the same market-data API family;
- direct fit with the optional Alpaca Paper shadow-execution gate later in the project;
- explicit authentication, rate-limit and feed behavior in the official documentation;
- supports a small US-equity universe, which matches the intended first experiment.

The provider abstraction remains independent of Alpaca. `MarketDataProvider` is the stable contract; Alpaca is only the first adapter.

## v1 data contract

Normalized quote fields:

- `symbol`
- `price`
- `currency`
- `observed_at`
- `market_open`
- `stale_after_seconds`

Normalized candle fields:

- `symbol`
- `start_at`
- `end_at`
- `open/high/low/close`
- `volume`
- `currency`

## Fail-closed policy

A quote is not eligible for a new simulated trade when:

- it is missing;
- it is older than the configured staleness threshold;
- the market is explicitly marked closed;
- the provider cannot prove a valid timestamp;
- a provider error prevents validation.

These cases must surface as explicit data states, not be translated into `NO_TRADE` by pretending the data was valid.

## Audit/replay

Raw normalized observations used for a decision can be persisted as sanitized snapshots. Provider credentials, request headers and secrets must never be written to those snapshots.

## External implementation deferred

No real Alpaca HTTP request belongs to this 20% → 25% gate. The next gate implements authentication, retries/rate-limits and real normalization while preserving the interface defined here.
