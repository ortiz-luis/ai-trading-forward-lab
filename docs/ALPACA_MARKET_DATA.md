# Alpaca Market Data adapter

This project uses Alpaca as the first real implementation of the provider-independent market-data contract.

## Official endpoints used

- Market data base: `https://data.alpaca.markets`
- Latest stock quote: `/v2/stocks/{symbol}/quotes/latest`
- Historical stock bars: `/v2/stocks/{symbol}/bars`
- Paper market clock: `https://paper-api.alpaca.markets/v2/clock`

Authentication uses request headers `APCA-API-KEY-ID` and `APCA-API-SECRET-KEY`.

## Environment variables

```bash
export ALPACA_API_KEY_ID='...'
export ALPACA_API_SECRET_KEY='...'
```

Never commit these values. In GitHub Actions they will later live in GitHub Secrets.

## Safe manual probe

```bash
python -m engine.providers.alpaca_probe
```

The probe prints only normalized provider health, a SPY quote and two normalized bars. It never prints request headers or credentials.

Without credentials it fails closed with a JSON error and exit code 2.

## Normalization choices

- Symbols are uppercase ASCII.
- Currency defaults to USD.
- The normalized quote price is the bid/ask midpoint when both are positive; if only one side is positive, that side is used.
- Market-open state comes from Alpaca's paper market clock endpoint rather than being guessed locally.
- Historical bars use 1-minute raw bars and are returned oldest-first after normalization.
- Provider timestamps are preserved as UTC-aware ISO timestamps.

## Failure behavior

- 401/403 -> authentication/permission failure, no retry.
- 429 -> bounded exponential retry, then explicit rate-limit error.
- 5xx/network -> bounded retry, then explicit provider failure.
- malformed/missing quote or bar payload -> explicit missing-data failure.
- credentials never appear in persisted observations, probe output or normalized health messages.

## Scope boundary

This adapter reads market data only. It cannot submit orders. Paper-broker execution remains a later optional gate and live trading remains outside the 0-100 simulation plan.
