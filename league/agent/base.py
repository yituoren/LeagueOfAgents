"""Agent Abstract Base Class"""

from __future__ import annotations

from abc import ABC, abstractmethod

from league.types import Action, Observation


class Agent(ABC):
    """Abstract Base Class for Agents

    Engine-driven, Agent passive response (Push mode).
    """

    def __init__(self, name: str) -> None:
        self.name = name

    @abstractmethod
    async def act(self, observation: Observation) -> Action:
        """Core interface: Decide on an action based on current observation"""
        pass

    def reset(self) -> None:
        """Reset agent state (e.g., clear memory)"""
        pass
