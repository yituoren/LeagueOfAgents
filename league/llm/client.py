"""Unified Asynchronous LLM Client based on OpenAI SDK"""

from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified Asynchronous LLM Client

    Based on the OpenAI SDK, compatible with all OpenAI-compatible APIs (e.g., DeepSeek, etc.).
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        api_key: str | None = "EMPTY",
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Asynchronous chat request, returns text response"""
        full_messages: list[dict[str, Any]] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,  # type: ignore[arg-type]
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM Chat Error: {e}")
            return f"Error: {e}"

    async def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system: str = "",
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Asynchronous chat request with tool calls"""
        full_messages: list[dict[str, Any]] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,  # type: ignore[arg-type]
                tools=tools,  # type: ignore[arg-type]
                temperature=temperature or self.temperature,
            )
            message = response.choices[0].message
            return {
                "content": message.content,
                "tool_calls": message.tool_calls,
            }
        except Exception as e:
            logger.error(f"LLM Tool Chat Error: {e}")
            return {"content": f"Error: {e}", "tool_calls": None}
