"""GameEngine Abstract Base Class: Game -> Round -> Step, Fully Asynchronous"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from league.logger.game_logger import GameLogger
from league.types import (
    Action,
    GameConfig,
    GameResult,
    Observation,
    Player,
    PlayerAction,
)

if TYPE_CHECKING:
    from league.referee.llm_referee import LLMReferee


class GameEngine(ABC):
    """Game Engine Abstract Base Class

    Three-layer structure:
    - Game: Manages the lifecycle of multiple rounds.
    - Round: Manages a single round of gameplay.
    - Step: The smallest unit of interaction.
    """

    def __init__(self, game_logger: GameLogger | None = None) -> None:
        self.players: list[Player] = []
        self.players_map: dict[str, Player] = {}
        self.config: GameConfig = GameConfig()
        self.game_logger = game_logger
        self.referee: LLMReferee | None = None
        self.current_round: int = 0
        self.current_step: int = 0

    # ========== Game Layer ==========

    async def run(self, players: list[Player], config: GameConfig) -> GameResult:
        """Main entry point (Template Method)"""
        self.players = players
        self.players_map = {p.player_id: p for p in players}
        self.config = config

        await self.on_game_start()

        self.current_round = 0
        while not self.is_game_over():
            await self.init_round(self.current_round)

            self.current_step = 0
            while (
                not self.is_round_over()
                and self.current_step < self.config.max_steps_per_round
            ):
                await self.execute_step()
                self.current_step += 1

            await self.end_round(self.current_round)
            self.current_round += 1

        return self.get_results()

    @abstractmethod
    async def on_game_start(self) -> None:
        """Initialization at the start of the game"""
        pass

    @abstractmethod
    def is_game_over(self) -> bool:
        """Determine if the entire game is over"""
        pass

    @abstractmethod
    def get_results(self) -> GameResult:
        """Return final game results"""
        pass

    # ========== Round Layer ==========

    @abstractmethod
    async def init_round(self, round_num: int) -> None:
        """Initialize round-level state"""
        pass

    @abstractmethod
    def is_round_over(self) -> bool:
        """Determine if the current round is over"""
        pass

    @abstractmethod
    async def end_round(self, round_num: int) -> None:
        """Cleanup after a round ends"""
        pass

    # ========== Step Layer ==========

    async def execute_step(self) -> None:
        """Execute a single step (Template Method)"""
        active_ids = self.get_active_players()
        if not active_ids:
            self.step_transition()
            return

        # Query players
        if self.is_concurrent_step():
            actions = await self.query_players_concurrent(active_ids)
        else:
            actions = await self.query_players_sequential(active_ids)

        # Apply actions and transition
        await self.apply_actions(actions)
        self.step_transition()

    @abstractmethod
    def get_active_players(self) -> list[str]:
        """Return IDs of players who need to act in this step"""
        pass

    def is_concurrent_step(self) -> bool:
        """Whether players act concurrently (True) or sequentially (False)"""
        return False

    @abstractmethod
    def build_observation(self, player_id: str) -> Observation:
        """Build a private observation for a specific player"""
        pass

    @abstractmethod
    def validate_action(self, player_id: str, action: Action) -> Action:
        """Validate and potentially correct a player's action"""
        pass

    @abstractmethod
    async def apply_actions(self, actions: list[PlayerAction]) -> None:
        """Update game state based on collected actions"""
        pass

    @abstractmethod
    def step_transition(self) -> None:
        """Transition to the next phase or step within the round"""
        pass

    # ========== Helpers ==========

    async def query_players_concurrent(
        self, player_ids: list[str]
    ) -> list[PlayerAction]:
        """Query multiple players simultaneously"""
        tasks = [self._query_single_player(pid) for pid in player_ids]
        results = await asyncio.gather(*tasks)
        # Sort by timestamp to maintain temporal order for concurrent actions
        return sorted(results, key=lambda x: x.timestamp)

    async def query_players_sequential(
        self, player_ids: list[str]
    ) -> list[PlayerAction]:
        """Query players one by one"""
        actions = []
        for pid in player_ids:
            action = await self._query_single_player(pid)
            actions.append(action)
        return actions

    async def _query_single_player(self, player_id: str) -> PlayerAction:
        """Internal helper to query a single agent"""
        player = self.players_map[player_id]
        obs = self.build_observation(player_id)

        start_time = time.time()
        try:
            # Enforce timeout if configured
            action = await asyncio.wait_for(
                player.agent.act(obs), timeout=self.config.timeout_seconds
            )
        except asyncio.TimeoutError:
            action = Action(action_type="timeout", content="")

        validated_action = self.validate_action(player_id, action)

        pa = PlayerAction(
            player_id=player_id, action=validated_action, timestamp=start_time
        )

        if self.game_logger:
            self.game_logger.log_action(pa, self.current_round, self.current_step)

        return pa
