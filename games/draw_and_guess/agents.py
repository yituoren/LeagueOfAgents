"""Specialized Agents for Draw and Guess"""

from __future__ import annotations

from games.draw_and_guess.prompts import DRAWER_SYSTEM_PROMPT, GUESSER_SYSTEM_PROMPT
from league.agent.llm_agent import LLMAgent
from league.llm.client import LLMClient
from league.tools.base import Tool


class DrawerAgent(LLMAgent):
    """Drawer Agent - uses image generation tool to create visual clues"""

    def __init__(
        self,
        name: str,
        llm_client: LLMClient,
        tools: list[Tool] | None = None,
    ) -> None:
        super().__init__(
            name=name,
            llm_client=llm_client,
            system_prompt=DRAWER_SYSTEM_PROMPT,
            tools=tools,
        )


class GuesserAgent(LLMAgent):
    """Guesser Agent"""

    def __init__(self, name: str, llm_client: LLMClient) -> None:
        super().__init__(
            name=name,
            llm_client=llm_client,
            system_prompt=GUESSER_SYSTEM_PROMPT,
        )
