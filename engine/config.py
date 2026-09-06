from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    environment: str = "local"
    starting_capital_eur: float = 1000.0


def load_settings(env: dict[str, str] | None = None) -> Settings:
    """Load deterministic local configuration without network or secrets.

    Only explicit environment variables are read. Defaults are stable and
    suitable for tests and local development.
    """
    source = os.environ if env is None else env
    environment = source.get("AITFL_ENV", "local")
    capital_raw = source.get("AITFL_STARTING_CAPITAL_EUR", "1000")
    capital = float(capital_raw)
    if capital <= 0:
        raise ValueError("AITFL_STARTING_CAPITAL_EUR must be > 0")
    return Settings(environment=environment, starting_capital_eur=capital)
