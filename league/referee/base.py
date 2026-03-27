"""Referee Abstract Base Class"""

from __future__ import annotations

from abc import ABC, abstractmethod

from league.types import JudgeContext, JudgeResult


class Referee(ABC):
    """Abstract Base Class for Referees"""

    @abstractmethod
    async def judge(self, context: JudgeContext) -> JudgeResult:
        """Judge a set of actions (e.g., semantic matching between guesses and target)"""
        pass
