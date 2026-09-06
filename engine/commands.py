from __future__ import annotations

from dataclasses import asdict

from .config import Settings


def decide(settings: Settings) -> dict[str, object]:
    """Offline placeholder for the future AI decision pipeline."""
    return {
        "command": "decide",
        "status": "ready",
        "network_used": False,
        "environment": settings.environment,
    }


def evaluate(settings: Settings) -> dict[str, object]:
    """Offline placeholder for the future deterministic evaluator."""
    return {
        "command": "evaluate",
        "status": "ready",
        "network_used": False,
        "environment": settings.environment,
    }


def rebuild(settings: Settings) -> dict[str, object]:
    """Offline placeholder for rebuilding derived state from future ledgers."""
    return {
        "command": "rebuild",
        "status": "ready",
        "network_used": False,
        "settings": asdict(settings),
    }
