"""Tool Abstract Base Class"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Result of a tool execution"""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Tool(ABC):
    """Abstract Base Class for Tools that agents can call via function calling"""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema for parameters

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given arguments"""
        ...

    def to_openai_schema(self) -> dict[str, Any]:
        """Convert to OpenAI function calling format"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
