"""Agent 抽象基类"""

from __future__ import annotations

from abc import ABC, abstractmethod

from league.types import Action, Observation


class Agent(ABC):
    """智能体抽象基类

    Engine驱动，Agent被动响应（Push模式）
    """

    @abstractmethod
    async def act(self, observation: Observation) -> Action:
        """唯一交互入口：接收观测，返回动作"""
        ...

    @abstractmethod
    def reset(self) -> None:
        """重置agent状态（新游戏开始时调用）"""
        ...
