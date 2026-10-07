"""MCP client for Sage — speaks Streamable HTTP with result-type narrowing."""
from __future__ import annotations

import time
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult, InputRequiredResult


class SageMCPClient:
    """Async context manager for Sage MCP server.

    Usage:
        async with SageMCPClient("http://localhost:8000/mcp") as client:
            tools = await client.list_tools()
            result = await client.call("get_pipeline_health", {})
    """

    def __init__(self, url: str) -> None:
        self._url = url
        self._cm: Any = None
        self._session: ClientSession | None = None

    async def __aenter__(self) -> SageMCPClient:
        self._cm = streamable_http_client(self._url)
        read_stream, write_stream = await self._cm.__aenter__()
        self._session = ClientSession(read_stream, write_stream)
        await self._session.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        if self._session is not None:
            await self._session.__aexit__(*exc_info)
            self._session = None
        if self._cm is not None:
            await self._cm.__aexit__(*exc_info)
            self._cm = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """Return list of tool descriptors from the server."""
        assert self._session is not None, "Client not connected"
        response = await self._session.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
            }
            for t in response.tools
        ]

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Call a tool and return its structured content.

        Narrows on result_type before reading structured_content to avoid
        AttributeError on InputRequiredResult responses.
        """
        assert self._session is not None, "Client not connected"
        result = await self._session.call_tool(name, arguments)
        return self._extract_structured(result)

    async def call_recorded(
        self, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Call a tool and return result with timing and provenance metadata."""
        assert self._session is not None, "Client not connected"
        start = time.perf_counter()
        result = await self._session.call_tool(name, arguments)
        duration_ms = (time.perf_counter() - start) * 1000

        structured = self._extract_structured(result)
        provenance = structured.get("provenance", "unknown")

        return {
            "name": name,
            "arguments": arguments,
            "duration_ms": round(duration_ms, 2),
            "result": structured,
            "provenance": provenance,
        }

    @staticmethod
    def _extract_structured(result: Any) -> dict[str, Any]:
        """Safely extract structured content from a call_tool result.

        Narrows on result_type to avoid AttributeError when the server
        returns an InputRequiredResult (which lacks structured_content).
        """
        result_type = getattr(result, "result_type", None)

        if result_type == "input_required":
            # InputRequiredResult — no structured_content field
            return {
                "result_type": "input_required",
                "input_requests": getattr(result, "input_requests", {}),
                "request_state": getattr(result, "request_state", ""),
            }

        if isinstance(result, CallToolResult):
            if result.is_error:
                return {
                    "result_type": "error",
                    "is_error": True,
                    "content": [
                        getattr(c, "text", str(c)) for c in (result.content or [])
                    ],
                }
            return result.structured_content or {}

        # Fallback: try structured_content, then content
        if hasattr(result, "structured_content"):
            return result.structured_content or {}
        if hasattr(result, "content"):
            return {
                "content": [
                    getattr(c, "text", str(c)) for c in (result.content or [])
                ]
            }
        return {}
