"""GameEngine 抽象基类：Game -> Round -> Step，全异步"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod

from league.types import (
    Action,
    GameConfig,
    GameResult,
    Observation,
    Player,
    PlayerAction,
)


class GameEngine(ABC):
    """游戏引擎抽象基类

    三层结构：
    - Game: 管理多局游戏
    - Round: 管理一局完整流程
    - Step: 最小交互单元
    """

    def __init__(self) -> None:
        self.players: dict[str, Player] = {}
        self.config: GameConfig = GameConfig()
        self.current_round: int = 0
        self.current_step: int = 0

    # ========== Game 层 ==========

    async def run(self, players: list[Player], config: GameConfig) -> GameResult:
        """主入口（模板方法）"""
        self.players = {p.player_id: p for p in players}
        self.config = config
        await self.on_game_start()
        self.current_round = 0
        while not self.is_game_over():
            await self.init_round(self.current_round)
            self.current_step = 0
            while not self.is_round_over():
                await self.execute_step()
                self.current_step += 1
            await self.end_round(self.current_round)
            self.current_round += 1
        return self.get_results()

    @abstractmethod
    async def on_game_start(self) -> None:
        """游戏开始时的初始化"""
        ...

    @abstractmethod
    def is_game_over(self) -> bool:
        """判断整个游戏是否结束"""
        ...

    @abstractmethod
    def get_results(self) -> GameResult:
        """获取最终游戏结果"""
        ...

    # ========== Round 层 ==========

    @abstractmethod
    async def init_round(self, round_num: int) -> None:
        """初始化一轮游戏（选词、分配角色等）"""
        ...

    @abstractmethod
    def is_round_over(self) -> bool:
        """判断当前轮是否结束"""
        ...

    @abstractmethod
    async def end_round(self, round_num: int) -> None:
        """结束一轮游戏（结算分数等）"""
        ...

    # ========== Step 层（模板方法 + 可重写子方法）==========

    async def execute_step(self) -> None:
        """执行一个step（模板方法，可整体重写）

        默认流程：
        1. get_active_players() -> 决定本step谁行动
        2. 根据 is_concurrent_step() 选择并发或顺序query
        3. apply_actions() -> 批量更新状态
        4. step_transition() -> 推进内部状态
        """
        active_players = self.get_active_players()

        if self.is_concurrent_step():
            actions = await self.query_players_concurrent(active_players)
        else:
            actions = await self.query_players_sequential(active_players)

        await self.apply_actions(actions)
        self.step_transition()

    async def query_players_concurrent(
        self, player_ids: list[str]
    ) -> list[PlayerAction]:
        """并发query多个玩家"""
        tasks = []
        for pid in player_ids:
            obs = self.build_observation(pid)
            tasks.append(self._query_single(pid, obs))
        results = await asyncio.gather(*tasks)
        return sorted(results, key=lambda x: x.timestamp)

    async def query_players_sequential(
        self, player_ids: list[str]
    ) -> list[PlayerAction]:
        """顺序query多个玩家"""
        actions: list[PlayerAction] = []
        for pid in player_ids:
            obs = self.build_observation(pid)
            action = await self.players[pid].agent.act(obs)
            validated = self.validate_action(pid, action)
            actions.append(PlayerAction(player_id=pid, action=validated))
        return actions

    async def _query_single(
        self, player_id: str, obs: Observation
    ) -> PlayerAction:
        """query单个玩家并记录时间戳"""
        action = await self.players[player_id].agent.act(obs)
        validated = self.validate_action(player_id, action)
        return PlayerAction(
            player_id=player_id, action=validated, timestamp=time.time()
        )

    # --- Step 层可重写子方法 ---

    @abstractmethod
    def get_active_players(self) -> list[str]:
        """决定本step哪些玩家需要行动"""
        ...

    def is_concurrent_step(self) -> bool:
        """本step是否并发query（默认False=顺序）"""
        return False

    @abstractmethod
    def build_observation(self, player_id: str) -> Observation:
        """为指定玩家构建观测（信息隔离核心）"""
        ...

    @abstractmethod
    def validate_action(self, player_id: str, action: Action) -> Action:
        """验证动作合法性"""
        ...

    @abstractmethod
    async def apply_actions(self, actions: list[PlayerAction]) -> None:
        """批量应用动作，更新游戏状态"""
        ...

    @abstractmethod
    def step_transition(self) -> None:
        """step内部状态转换"""
        ...
