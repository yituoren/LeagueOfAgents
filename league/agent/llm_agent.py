"""LLM-driven Agent implementation"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from league.agent.base import Agent
from league.agent.memory import Memory, MemoryEntry
from league.llm.client import LLMClient
from league.prompts.agent import AGENT_BASE_PROMPT
from league.tools.base import Tool
from league.types import Action, Observation

logger = logging.getLogger(__name__)


class LLMAgent(Agent):
    """LLM-based Agent

    Uses LLMClient to call Large Language Models.
    Supports tool calling (ReAct loop) and agent-controlled memory via <memory> tags.
    """

    def __init__(
        self,
        name: str,
        llm_client: LLMClient,
        system_prompt: str = "",
        memory_capacity: int = 50,
        tools: list[Tool] | None = None,
    ) -> None:
        super().__init__(name)
        self.llm_client = llm_client
        self.system_prompt = self._compose_system_prompt(system_prompt)
        self.memory = Memory(short_term_capacity=memory_capacity)
        self.tools = tools or []

    async def act(self, observation: Observation) -> Action:
        """Receive observation and call LLM to generate action"""
        messages = self._build_messages(observation)

        if not self.tools:
            response = await self.llm_client.chat(
                messages=messages,
                system=self.system_prompt,
            )
            content = response.strip()
        else:
            content, tool_results = await self._act_with_tools(messages)

        action = self._parse_response(content, observation)

        # Extract and save <memory> tags (agent-controlled)
        self._extract_and_save_memories(content, observation)

        if self.tools and tool_results:
            action.metadata["tool_results"] = tool_results

        return action

    def reset(self) -> None:
        """Reset agent state"""
        self.memory.clear()

    # ========== Prompt Composition ==========

    @staticmethod
    def _compose_system_prompt(game_prompt: str) -> str:
        """Compose full system prompt: base + game-specific"""
        if not game_prompt:
            return AGENT_BASE_PROMPT
        return f"{AGENT_BASE_PROMPT}\n---\n\n{game_prompt}"

    # ========== Tool Calling ==========

    async def _act_with_tools(
        self, messages: list[dict[str, Any]]
    ) -> tuple[str, list[dict[str, Any]]]:
        """Run tool calling loop until LLM produces a final text response"""
        tool_schemas = [t.to_openai_schema() for t in self.tools]
        tool_results: list[dict[str, Any]] = []

        while True:
            result = await self.llm_client.chat_with_tools(
                messages=messages,
                tools=tool_schemas,
                system=self.system_prompt,
            )

            tool_calls = result.get("tool_calls")
            if not tool_calls:
                return result.get("content", "") or "", tool_results

            # Append assistant message with tool calls
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": result.get("content") or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
            messages.append(assistant_msg)

            # Execute each tool call and append results
            for tc in tool_calls:
                tool = self._find_tool(tc.function.name)
                if tool:
                    try:
                        kwargs = json.loads(tc.function.arguments)
                    except json.JSONDecodeError:
                        kwargs = {}
                    tr = await tool.execute(**kwargs)
                    tool_results.append(
                        {
                            "tool_name": tc.function.name,
                            "arguments": kwargs,
                            "result": tr.content,
                            "metadata": tr.metadata,
                        }
                    )
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": tr.content,
                        }
                    )
                    logger.info(
                        f"[{self.name}] Tool '{tc.function.name}' executed: {tr.content[:100]}"
                    )
                else:
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": f"Error: Unknown tool '{tc.function.name}'",
                        }
                    )

    def _find_tool(self, name: str) -> Tool | None:
        for t in self.tools:
            if t.name == name:
                return t
        return None

    # ========== Memory ==========

    def _extract_and_save_memories(
        self, content: str, observation: Observation
    ) -> None:
        """Parse <memory> tags from LLM output and save to memory"""
        matches = re.findall(r"<memory>(.*?)</memory>", content, re.DOTALL)
        for mem_text in matches:
            mem_text = mem_text.strip()
            if mem_text:
                self.memory.add(
                    MemoryEntry(
                        content=mem_text,
                        round_num=observation.round_num,
                        step_num=observation.step_num,
                    )
                )
                logger.debug(f"[{self.name}] Saved memory: {mem_text[:60]}...")

    # ========== Message Building ==========

    def _build_messages(self, observation: Observation) -> list[dict[str, Any]]:
        """Build message list for LLM"""
        messages: list[dict[str, Any]] = []

        # Provide agent's self-saved memories
        all_memories = self.memory.get_recent(self.memory.short_term.maxlen or 50)
        if all_memories:
            memory_lines = [f"- {e.content}" for e in all_memories]
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "[Your Saved Memories]\n"
                        "These are notes you wrote to yourself in previous turns:\n"
                        + "\n".join(memory_lines)
                    ),
                }
            )

        # Current observation
        obs_text = f"Current State: {observation.visible_state}\n"
        if observation.player_role:
            obs_text += f"Your Role: {observation.player_role}\n"
        obs_text += f"Task: {observation.action_prompt}"

        messages.append(
            {
                "role": "user",
                "content": obs_text,
            }
        )

        return messages

    # ========== Response Parsing ==========

    def _parse_response(self, content: str, observation: Observation) -> Action:
        """Parse LLM output, extracting content from <output> tags"""
        # Extract <output> content
        output_match = re.search(r"<output>(.*?)</output>", content, re.DOTALL)
        if output_match:
            action_content = output_match.group(1).strip()
        else:
            # Fallback: strip <thought> and <memory> tags
            action_content = re.sub(
                r"<(?:thought|memory)>.*?</(?:thought|memory)>",
                "",
                content,
                flags=re.DOTALL,
            ).strip()

        if not action_content:
            action_content = content

        return Action(
            action_type="speak",
            content=action_content,
            metadata={"raw_response": content},
        )
