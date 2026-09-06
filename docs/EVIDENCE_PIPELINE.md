# Context and evidence pipeline v1

This layer decides which factual material is allowed into an AI decision context. It is deliberately separate from the model provider and from the future evaluator.

## Evidence record

Every item must carry:

- absolute `http(s)` URL;
- source name;
- source class: `PRIMARY` or `SECONDARY`;
- title;
- publication timestamp;
- retrieval timestamp;
- concise summary.

The v1 policy fails closed on undated material.

## Source priority

Primary evidence is ranked before secondary evidence. Examples of primary evidence are issuer investor-relations releases, SEC/regulatory filings, exchange notices and official company statements. Secondary evidence is established financial/news reporting that contextualizes a primary fact.

The pipeline itself does not fetch the web yet. It validates and bounds records supplied by the future retrieval/context builder. This separation keeps web retrieval replaceable without changing the audit contract.

## Temporal rules

All decision evidence is evaluated against a locked `cutoff_at`.

- `published_at` must be at or before the cutoff.
- `retrieved_at` must be at or before the cutoff in v1.
- undated evidence is rejected.
- default maximum age: 7 days for primary evidence and 72 hours for secondary evidence.
- these age windows are protocol inputs and can only change in a later cohort/version once v1 starts.

These rules prevent post-cutoff or stale material from silently being described as contemporaneous.

## Bounded context

The default decision context contains at most 12 evidence records. After validation, records are sorted deterministically:

1. primary before secondary;
2. newest publication first;
3. URL as deterministic tie-breaker.

This bounds model context/cost and prevents a changing search result count from changing the pipeline arbitrarily.

## Audit manifest

`write_evidence_manifest()` writes the exact evidence set used for a decision, including `cutoff_at`, record count and a SHA-256 hash of the canonical record list. The manifest is intended to be associated with the immutable decision event.

The manifest contains public evidence metadata only. It must never contain API keys, authorization headers, cookies or hidden provider state.

## Failure semantics

The pipeline raises explicit errors for:

- post-cutoff publication or retrieval;
- stale evidence;
- missing publication time;
- malformed URLs/timestamps/records.

A failure here is a context/data failure, not `NO_TRADE`. The later orchestration layer must not transform evidence-pipeline failure into a market opinion.

## Gate boundary

This 45%→50% gate defines evidence normalization, temporal validity, deterministic prioritization, bounded context and manifests. Actual web/news retrieval and automated orchestration remain separate concerns.
