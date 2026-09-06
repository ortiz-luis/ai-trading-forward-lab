from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol

from openai import OpenAI

from ..decision_contract import DECISION_JSON_SCHEMA, DecisionInput, DecisionOutput, build_prompt_input


class DecisionProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class DecisionProviderResult:
    decision: DecisionOutput | None
    model: str
    response_id: str | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    repaired: bool
    error_code: str | None = None
    error_message: str | None = None

    @property
    def ok(self) -> bool:
        return self.decision is not None and self.error_code is None


class ResponsesClient(Protocol):
    class _Responses(Protocol):
        def create(self, **kwargs: Any) -> Any: ...

    responses: _Responses


class OpenAIDecisionProvider:
    """OpenAI Responses API adapter for the simulation-only decision contract."""

    name = "openai"

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 2,
        client: ResponsesClient | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be > 0")
        if max_retries < 0 or max_retries > 3:
            raise ValueError("max_retries must be between 0 and 3")

        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5.6-terra")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        if client is not None:
            self._client = client
        else:
            resolved_key = api_key or os.environ.get("OPENAI_API_KEY")
            if not resolved_key:
                raise DecisionProviderError("OPENAI_API_KEY is not configured")
            self._client = OpenAI(
                api_key=resolved_key,
                timeout=timeout_seconds,
                max_retries=max_retries,
            )

    def decide(self, input_data: DecisionInput, *, instructions: str) -> DecisionProviderResult:
        payload = build_prompt_input(input_data)
        try:
            response = self._create_response(payload=payload, instructions=instructions)
            parsed = self._parse_response(response)
            self._validate_sources_against_input(parsed, payload)
            return self._success_result(parsed, response=response, repaired=False)
        except Exception as first_error:
            try:
                repair_payload = {
                    "task": "repair_invalid_structured_output",
                    "original_input": payload,
                    "validation_error": str(first_error),
                }
                response = self._create_response(
                    payload=repair_payload,
                    instructions=(
                        instructions
                        + "\nReturn a fresh answer that strictly satisfies the supplied JSON schema and protocol."
                    ),
                )
                parsed = self._parse_response(response)
                self._validate_sources_against_input(parsed, payload)
                return self._success_result(parsed, response=response, repaired=True)
            except Exception as repair_error:
                return DecisionProviderResult(
                    decision=None,
                    model=self.model,
                    response_id=None,
                    input_tokens=None,
                    output_tokens=None,
                    total_tokens=None,
                    repaired=True,
                    error_code="AI_ERROR",
                    error_message=f"primary={first_error}; repair={repair_error}",
                )

    def _create_response(self, *, payload: dict[str, Any], instructions: str) -> Any:
        return self._client.responses.create(
            model=self.model,
            instructions=instructions,
            input=json.dumps(payload, sort_keys=True, ensure_ascii=False),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "trading_decision_v1",
                    "strict": True,
                    "schema": DECISION_JSON_SCHEMA,
                }
            },
            store=False,
            metadata={"component": "ai-trading-forward-lab", "prompt_version": "trading-v1"},
        )

    @staticmethod
    def _parse_response(response: Any) -> DecisionOutput:
        status = getattr(response, "status", None)
        if status not in (None, "completed"):
            raise DecisionProviderError(f"response status is {status}")
        text = getattr(response, "output_text", None)
        if not isinstance(text, str) or not text.strip():
            raise DecisionProviderError("response has no output_text")
        try:
            raw = json.loads(text)
        except json.JSONDecodeError as exc:
            raise DecisionProviderError("response output_text is not valid JSON") from exc
        return DecisionOutput.from_dict(raw)

    @staticmethod
    def _validate_sources_against_input(decision: DecisionOutput, payload: dict[str, Any]) -> None:
        evidence = payload.get("evidence")
        if not isinstance(evidence, list):
            raise DecisionProviderError("input evidence must be a list")
        allowed = {
            (row.get("url"), row.get("published_at"))
            for row in evidence
            if isinstance(row, dict)
        }
        for source in decision.sources:
            candidate = (source.get("url"), source.get("published_at"))
            if candidate not in allowed:
                raise DecisionProviderError("decision referenced evidence not present in supplied context")

    def _success_result(self, decision: DecisionOutput, *, response: Any, repaired: bool) -> DecisionProviderResult:
        usage = getattr(response, "usage", None)
        return DecisionProviderResult(
            decision=decision,
            model=str(getattr(response, "model", self.model)),
            response_id=getattr(response, "id", None),
            input_tokens=getattr(usage, "input_tokens", None) if usage is not None else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage is not None else None,
            total_tokens=getattr(usage, "total_tokens", None) if usage is not None else None,
            repaired=repaired,
        )
