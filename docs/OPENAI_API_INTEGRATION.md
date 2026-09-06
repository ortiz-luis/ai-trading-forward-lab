# OpenAI API integration — gate 40% → 45%

## Purpose

This adapter connects the simulation-only decision contract to the official OpenAI Python SDK and Responses API. It does not send brokerage instructions and it does not contain any live-broker capability.

## Configuration

Required environment variable:

- `OPENAI_API_KEY`

Optional:

- `OPENAI_MODEL` (default: `gpt-5.6-terra`)

The API key must be supplied through WSL environment variables or GitHub Actions Secrets. It must never be committed, embedded in GitHub Pages, written to JSON artifacts, or printed by the probe.

## Request contract

The adapter uses the Responses API with Structured Outputs:

- `text.format.type = json_schema`
- `strict = true`
- the schema is `DECISION_JSON_SCHEMA`
- `store = false`
- prompt version is recorded in metadata

The prompt is loaded from `prompts/trading_v1.md`.

## Failure behavior

The provider uses a bounded SDK retry policy plus exactly one application-level structured repair attempt when the first result cannot be parsed/validated. If both attempts fail, the result is explicit `AI_ERROR` with `decision=None`.

An API/network/schema failure must never be converted into `NO_TRADE`; `NO_TRADE` means the model successfully decided not to allocate simulated capital.

## Usage metadata

When returned by the API, the adapter records only non-secret metadata:

- response ID
- actual model identifier
- input tokens
- output tokens
- total tokens
- whether the repair path was used

This makes later cost accounting possible without persisting credentials.

## Manual safe probe

After installing the project and exporting `OPENAI_API_KEY`:

```bash
python -m engine.providers.openai_probe
```

The probe uses a clearly synthetic market fixture. It prints a sanitized result only. With no key it fails cleanly before any request.

## Model choice

The default is `gpt-5.6-terra`, chosen as a cost/intelligence balance for one scheduled decision per trading day. The model is environment-configurable, and the final cohort model will be frozen during the 90% → 95% experiment-freeze gate.

## Verification status

Unit tests use a fake Responses client, so success, malformed JSON, protocol-invalid output, repair, usage metadata and dual-failure paths can be checked without network access or secrets. A live probe is intentionally impossible until the user supplies an OpenAI API key outside the repository.
