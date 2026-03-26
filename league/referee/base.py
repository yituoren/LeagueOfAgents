"""Referee 抽象基类"""

from __future__ import annotations

from abc import ABC, abstractmethod

from league.types import JudgeContext, JudgeResult


class Referee(ABC):
    """裁判抽象基类"""

    @abstractmethod
    async def judge(self, context: JudgeContext) -> JudgeResult:
        """判定（如：语义匹配猜测与答案）"""
        ...
