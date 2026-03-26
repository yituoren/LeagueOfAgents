"""你画我猜专用Agent"""

from __future__ import annotations

from league.agent.llm_agent import LLMAgent
from league.llm.client import LLMClient
from games.draw_and_guess.prompts import DRAWER_SYSTEM_PROMPT, GUESSER_SYSTEM_PROMPT


class DrawerAgent(LLMAgent):
    """作画者Agent"""

    def __init__(self, name: str, llm_client: LLMClient) -> None:
        super().__init__(
            name=name,
            llm_client=llm_client,
            system_prompt=DRAWER_SYSTEM_PROMPT,
        )


class GuesserAgent(LLMAgent):
    """猜词者Agent"""

    def __init__(self, name: str, llm_client: LLMClient) -> None:
        super().__init__(
            name=name,
            llm_client=llm_client,
            system_prompt=GUESSER_SYSTEM_PROMPT,
        )
