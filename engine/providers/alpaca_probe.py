from __future__ import annotations

from dataclasses import asdict
import json
import sys

from .alpaca import AlpacaMarketDataProvider, AlpacaProviderError


def main() -> int:
    try:
        provider = AlpacaMarketDataProvider()
        quote = provider.get_quote("SPY")
        candles = provider.get_candles("SPY", limit=2)
        payload = {
            "provider": provider.name,
            "health": asdict(provider.health),
            "quote": asdict(quote),
            "candles": [asdict(row) for row in candles],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    except AlpacaProviderError as exc:
        # Deliberately print only the normalized error message, never headers or secrets.
        print(json.dumps({"provider": "alpaca", "status": "error", "message": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
