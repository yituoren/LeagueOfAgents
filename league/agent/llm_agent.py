"""LLM-driven Agent implementation"""

from __future__ import annotations

import re

from league.agent.base import Agent
from league.agent.memory import Memory, MemoryEntry
from league.llm.client import LLMClient
from league.types import Action, Observation


class LLMAgent(Agent):
    """LLM-based Agent

    Uses LLMClient to call Large Language Models, supports memory management and Chain-of-Thought.
    """

    def __init__(
        self,
        name: str,
        llm_client: LLMClient,
        system_prompt: str = "",
        memory_capacity: int = 50,
    ) -> None:
        super().__init__(name)
        self.llm_client = llm_client
        self.system_prompt = system_prompt
        self.memory = Memory(short_term_capacity=memory_capacity)

    async def act(self, observation: Observation) -> Action:
        """Receive observation and call LLM to generate action"""
        messages = self._build_messages(observation)
        response = await self.llm_client.chat(
            messages=messages,
            system=self.system_prompt,
        )

        content = response.strip()
        action = self._parse_response(content, observation)

        # Record action in memory
        self.memory.add(
            MemoryEntry(
                content=f"Observation: {observation.action_prompt}\nAction: {action.content}",
                metadata={"round": observation.round_num, "step": observation.step_num},
            )
        )

        return action

    def reset(self) -> None:
        """Reset agent state"""
        self.memory.clear()

    def _build_messages(self, observation: Observation) -> list[dict[str, str]]:
        """Build message list for LLM"""
        messages: list[dict[str, str]] = []

        # Inject recent memory
        recent = self.memory.get_recent(10)
        if recent:
            memory_text = "\n".join(e.content for e in recent)
            messages.append(
                {
                    "role": "user",
                    "content": f"[Past Memory]\n{memory_text}",
                }
            )

        # Inject current observation
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

    def _parse_response(self, content: str, observation: Observation) -> Action:
        """Parse LLM output, extracting content from <output> tags if present"""
        # Try to extract content within <output> tags
        output_match = re.search(r"<output>(.*?)</output>", content, re.DOTALL)
        if output_match:
            action_content = output_match.group(1).strip()
        else:
            # Fallback: remove <thought> tags if they exist
            action_content = re.sub(
                r"<thought>.*?</thought>", "", content, flags=re.DOTALL
            ).strip()

        # If still empty, use the original content
        if not action_content:
            action_content = content

        return Action(
            action_type="speak",
            content=action_content,
            metadata={"raw_response": content},
        )
