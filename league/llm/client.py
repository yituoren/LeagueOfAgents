"""基于OpenAI SDK的统一异步LLM客户端"""

from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """统一异步LLM客户端

    基于OpenAI SDK，兼容所有OpenAI-compatible API（如DeepSeek等）。
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def chat(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """异步聊天请求，返回文本响应"""
        full_messages: list[dict[str, str]] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,  # type: ignore[arg-type]
            temperature=temperature or self.temperature,
            max_tokens=max_tokens or self.max_tokens,
        )
        content = response.choices[0].message.content
        return content or ""

    async def chat_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        system: str = "",
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """异步带工具调用的聊天请求"""
        full_messages: list[dict[str, str]] = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,  # type: ignore[arg-type]
            tools=tools,  # type: ignore[arg-type]
            temperature=temperature or self.temperature,
        )
        choice = response.choices[0]
        result: dict[str, Any] = {
            "content": choice.message.content or "",
            "tool_calls": [],
        }
        if choice.message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]
        return result
