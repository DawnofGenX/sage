"""LLM API format handlers.

Supports OpenAI-compatible chat/completions endpoints and Anthropic Claude
messages endpoints. The wire format is auto-detected from the API URL via
:func:`detect_format`.
"""

from __future__ import annotations

import json
import re
from typing import Any, Protocol


class LLMAPIFormat(Protocol):
    """Protocol describing an LLM API wire format."""

    name: str

    def build_payload(self, model: str, prompt: str) -> dict[str, Any]:
        """Build the JSON request body for a completion call."""
        ...

    def build_headers(self, api_key: str) -> dict[str, str]:
        """Build the HTTP headers for a completion call."""
        ...

    def validate_response(self, data: dict[str, Any]) -> None:
        """Raise ValueError if the response payload is malformed."""
        ...

    def extract_content(self, data: dict[str, Any]) -> str:
        """Extract the raw text content from a validated response."""
        ...


class OpenAIFormat:
    """OpenAI-compatible chat/completions format."""

    name = "openai"

    def build_payload(self, model: str, prompt: str) -> dict[str, Any]:
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }

    def build_headers(self, api_key: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def validate_response(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict) or not data.get("choices"):
            raise ValueError("Invalid OpenAI response: missing 'choices'")

    def extract_content(self, data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Malformed OpenAI response content: {exc}") from exc
        if not isinstance(content, str):
            raise ValueError("OpenAI response content is not a string")
        return content


class AnthropicFormat:
    """Anthropic Claude messages format."""

    name = "anthropic"

    def build_payload(self, model: str, prompt: str) -> dict[str, Any]:
        return {
            "model": model,
            "max_tokens": 4096,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }

    def build_headers(self, api_key: str) -> dict[str, str]:
        return {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def validate_response(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict) or not data.get("content"):
            raise ValueError("Invalid Anthropic response: missing 'content'")

    def extract_content(self, data: dict[str, Any]) -> str:
        try:
            content = data["content"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Malformed Anthropic response content: {exc}") from exc
        if not isinstance(content, str):
            raise ValueError("Anthropic response content is not a string")
        return content


def detect_format(api_url: str | None) -> LLMAPIFormat:
    """Auto-detect the API format from the URL.

    URLs containing ``anthropic`` use the Anthropic messages format;
    everything else defaults to the OpenAI-compatible chat/completions
    format (which also covers OpenRouter, Together, local Ollama, etc.).
    """
    url = (api_url or "").lower()
    if "anthropic" in url:
        return AnthropicFormat()
    return OpenAIFormat()


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences (```json ... ```) from an LLM response."""
    stripped = text.strip()
    match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return stripped


def parse_json_response(content: str) -> dict[str, Any]:
    """Parse JSON from an LLM response, tolerating markdown code fences.

    Raises:
        ValueError: If the content is not valid JSON or not a JSON object.
    """
    text = strip_code_fences(content)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM response is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("LLM response must be a JSON object")
    return data
