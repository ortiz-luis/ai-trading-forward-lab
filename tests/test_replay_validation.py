from __future__ import annotations

import pytest

from engine.replay_validation import ReplayArtifactError, validate_professional_replay_payload


def base_payload():
    return {
        "version": "professional-v2",
        "forward_ledger_untouched": True,
        "sessions": [{
            "replay_id": "r1",
            "cutoff_at": "2026-09-01T20:05:00Z",
            "cutoff_date": "2026-09-01",
            "evidence": [{"url": "https://example.com/a", "published_at": "2026-09-01T12:00:00Z"}],
            "chart": {
                "symbol": "AAPL",
                "candles_before_cutoff": [{"date": "2026-09-01"}],
                "candles_after_cutoff": [{"date": "2026-09-02"}],
                "spy_before_cutoff": [{"date": "2026-09-01"}],
                "spy_after_cutoff": [{"date": "2026-09-02"}],
            },
            "decision": {"action": "BUY", "symbol": "AAPL"},
            "lifecycle": [{"date": "2026-09-02"}],
            "result": {"available": True, "entry_day": "2026-09-02", "exit_day": "2026-09-02"},
        }],
    }


def test_valid_professional_replay_payload_passes():
    validate_professional_replay_payload(base_payload())


def test_future_evidence_fails_closed():
    payload = base_payload()
    payload["sessions"][0]["evidence"][0]["published_at"] = "2026-09-02T12:00:00Z"
    with pytest.raises(ReplayArtifactError, match="post-cutoff evidence"):
        validate_professional_replay_payload(payload)


def test_future_candle_in_visible_history_fails_closed():
    payload = base_payload()
    payload["sessions"][0]["chart"]["candles_before_cutoff"][0]["date"] = "2026-09-02"
    with pytest.raises(ReplayArtifactError, match="future candle"):
        validate_professional_replay_payload(payload)
