import json

import pytest

from engine.evidence import (
    EvidenceKind,
    EvidencePolicy,
    EvidenceRecord,
    PostCutoffEvidence,
    StaleEvidence,
    UndatedEvidence,
    build_evidence_context,
    write_evidence_manifest,
)


CUTOFF = "2026-09-06T14:00:00Z"


def rec(*, url, kind, published_at, retrieved_at="2026-09-06T13:55:00Z"):
    return EvidenceRecord(
        url=url,
        source_name="fixture",
        kind=kind,
        title="fixture title",
        published_at=published_at,
        retrieved_at=retrieved_at,
        summary="fixture summary",
    )


def test_primary_sources_rank_before_secondary():
    records = [
        rec(url="https://news.example/a", kind=EvidenceKind.SECONDARY, published_at="2026-09-06T13:50:00Z"),
        rec(url="https://ir.example/b", kind=EvidenceKind.PRIMARY, published_at="2026-09-06T12:00:00Z"),
    ]
    context = build_evidence_context(records, cutoff_at=CUTOFF)
    assert context[0].kind == EvidenceKind.PRIMARY


def test_context_is_bounded_and_deterministic():
    policy = EvidencePolicy(max_items=2)
    records = [
        rec(url=f"https://ir.example/{i}", kind=EvidenceKind.PRIMARY, published_at=f"2026-09-06T1{i}:00:00Z")
        for i in range(1, 4)
    ]
    a = build_evidence_context(records, cutoff_at=CUTOFF, policy=policy)
    b = build_evidence_context(reversed(records), cutoff_at=CUTOFF, policy=policy)
    assert [x.url for x in a] == [x.url for x in b]
    assert len(a) == 2


def test_post_cutoff_publication_fails_closed():
    row = rec(url="https://ir.example/future", kind=EvidenceKind.PRIMARY, published_at="2026-09-06T14:01:00Z")
    with pytest.raises(PostCutoffEvidence):
        build_evidence_context([row], cutoff_at=CUTOFF)


def test_post_cutoff_retrieval_fails_closed():
    row = rec(
        url="https://ir.example/future-retrieval",
        kind=EvidenceKind.PRIMARY,
        published_at="2026-09-06T13:00:00Z",
        retrieved_at="2026-09-06T14:01:00Z",
    )
    with pytest.raises(PostCutoffEvidence):
        build_evidence_context([row], cutoff_at=CUTOFF)


def test_stale_secondary_fails_closed():
    row = rec(url="https://news.example/old", kind=EvidenceKind.SECONDARY, published_at="2026-09-01T12:00:00Z")
    with pytest.raises(StaleEvidence):
        build_evidence_context([row], cutoff_at=CUTOFF)


def test_undated_evidence_fails_closed():
    row = rec(url="https://news.example/undated", kind=EvidenceKind.SECONDARY, published_at=None)
    with pytest.raises(UndatedEvidence):
        build_evidence_context([row], cutoff_at=CUTOFF)


def test_manifest_is_auditable_and_stable(tmp_path):
    rows = build_evidence_context([
        rec(url="https://ir.example/a", kind=EvidenceKind.PRIMARY, published_at="2026-09-06T12:00:00Z"),
        rec(url="https://news.example/b", kind=EvidenceKind.SECONDARY, published_at="2026-09-06T13:00:00Z"),
    ], cutoff_at=CUTOFF)
    path = tmp_path / "manifest.json"
    payload = write_evidence_manifest(path, rows, cutoff_at=CUTOFF)
    restored = json.loads(path.read_text())
    assert restored["records_sha256"] == payload["records_sha256"]
    assert restored["count"] == 2
    assert all("url" in item and "published_at" in item and "retrieved_at" in item for item in restored["records"])
