from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any
from urllib import error, request

from ..schemas import Action, DecisionEvent

PAPER_BASE_URL = "https://paper-api.alpaca.markets"
LIVE_BASE_URL = "https://api.alpaca.markets"


class PaperShadowError(RuntimeError):
    pass


@dataclass(frozen=True)
class PaperFill:
    order_id: str
    symbol: str
    side: str
    status: str
    filled_qty: float
    filled_avg_price: float | None


class AlpacaPaperShadow:
    """Optional mirror into Alpaca Paper only.

    This adapter is never the source of truth. It accepts already-validated
    simulated decisions and returns paper-order metadata for reconciliation.
    Live Alpaca endpoints are hard-blocked.
    """

    name = "alpaca-paper-shadow"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str = PAPER_BASE_URL,
        timeout_seconds: float = 15.0,
    ) -> None:
        if base_url.rstrip("/") != PAPER_BASE_URL:
            raise PaperShadowError("live/non-paper Alpaca endpoint is forbidden")
        if LIVE_BASE_URL in base_url:
            raise PaperShadowError("live Alpaca endpoint is forbidden")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        self.api_key = api_key or os.getenv("ALPACA_PAPER_API_KEY")
        self.api_secret = api_secret or os.getenv("ALPACA_PAPER_API_SECRET")
        if not self.api_key or not self.api_secret:
            raise PaperShadowError("Alpaca Paper credentials are not configured")
        self.base_url = PAPER_BASE_URL
        self.timeout_seconds = timeout_seconds

    def mirror_decision(self, decision: DecisionEvent, *, reference_price_usd: float) -> PaperFill | None:
        decision.validate()
        if reference_price_usd <= 0:
            raise ValueError("reference_price_usd must be > 0")
        if decision.action in {Action.NO_TRADE, Action.HOLD}:
            return None
        if not decision.symbol:
            raise PaperShadowError("symbol is required")

        if decision.action == Action.BUY:
            if decision.notional_eur <= 0:
                raise PaperShadowError("BUY requires positive simulated notional")
            # Paper shadow uses a fractional share estimate only for mirroring.
            qty = decision.notional_eur / reference_price_usd
            payload = {
                "symbol": decision.symbol,
                "qty": f"{qty:.8f}",
                "side": "buy",
                "type": "market",
                "time_in_force": "day",
            }
        elif decision.action == Action.SELL:
            payload = {
                "symbol": decision.symbol,
                "side": "sell",
                "type": "market",
                "time_in_force": "day",
                "position_intent": "sell_to_close",
            }
        else:
            raise PaperShadowError(f"unsupported action {decision.action}")

        raw = self._json_request("POST", "/v2/orders", payload)
        return self._normalize_fill(raw, symbol=decision.symbol, side=payload["side"])

    def reconcile_order(self, order_id: str) -> PaperFill:
        if not order_id.strip():
            raise ValueError("order_id is required")
        raw = self._json_request("GET", f"/v2/orders/{order_id}", None)
        return self._normalize_fill(raw)

    def _json_request(self, method: str, path: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.base_url + path,
            data=body,
            method=method,
            headers={
                "APCA-API-KEY-ID": self.api_key,
                "APCA-API-SECRET-KEY": self.api_secret,
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            raise PaperShadowError(f"paper API HTTP {exc.code}") from exc
        except error.URLError as exc:
            raise PaperShadowError("paper API network error") from exc

    @staticmethod
    def _normalize_fill(raw: dict[str, Any], *, symbol: str | None = None, side: str | None = None) -> PaperFill:
        return PaperFill(
            order_id=str(raw.get("id", "")),
            symbol=str(raw.get("symbol", symbol or "")),
            side=str(raw.get("side", side or "")),
            status=str(raw.get("status", "unknown")),
            filled_qty=float(raw.get("filled_qty") or 0.0),
            filled_avg_price=(
                float(raw["filled_avg_price"])
                if raw.get("filled_avg_price") not in (None, "")
                else None
            ),
        )
