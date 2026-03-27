"""Draw and Guess Game Engine"""

from __future__ import annotations

import logging
import random
from enum import Enum

from games.draw_and_guess.prompts import (
    DRAWER_ACTION_PROMPT,
    GUESSER_ACTION_PROMPT,
)
from league.engine.base import GameEngine
from league.logger.game_logger import GameLogger
from league.types import (
    Action,
    GameConfig,
    GameResult,
    Observation,
    Player,
    PlayerAction,
)

logger = logging.getLogger(__name__)

# Default word pool
DEFAULT_WORDS = [
    "Apple",
    "Sun",
    "Moon",
    "Cat",
    "Airplane",
    "Snowflake",
    "Guitar",
    "Castle",
    "Rainbow",
    "Robot",
    "Volcano",
    "Diamond",
    "Butterfly",
    "Telescope",
    "Lighthouse",
]


class GamePhase(Enum):
    """Game Phases"""

    DRAWING = "drawing"
    GUESSING = "guessing"
    SETTLEMENT = "settlement"


class DrawAndGuessEngine(GameEngine):
    """Draw and Guess Game Engine

    Game: N Rounds (Each player takes turns as the Drawer)
      Round (Player X draws):
        Step 1 [sequential]: Query Drawer -> Return scene description
        Step 2 [concurrent]: Query Guessers -> Guess simultaneously
        Step 3 [internal]: Referee judgment + Scoring
    """

    def __init__(self, game_logger: GameLogger | None = None) -> None:
        super().__init__(game_logger)
        self.word_pool = DEFAULT_WORDS.copy()
        self.current_drawer_idx = 0
        self.current_target_word = ""
        self.current_description = ""
        self.phase = GamePhase.DRAWING
        self.round_scores = {}

    async def on_game_start(self) -> None:
        """Initialize game-level state"""
        config_extra = self.config.extra or {}
        custom_words = config_extra.get("word_pool", [])
        if custom_words:
            self.word_pool = custom_words.copy()

        random.shuffle(self.word_pool)
        self.current_drawer_idx = 0
        logger.info(
            f"Game started with {len(self.players)} players, {self.config.num_rounds} rounds."
        )

    def is_game_over(self) -> bool:
        """Game ends after N rounds"""
        return self.current_round >= self.config.num_rounds

    def get_results(self) -> GameResult:
        """Aggregate final rankings"""
        sorted_players = sorted(self.players, key=lambda p: p.score, reverse=True)
        return GameResult(
            winner_ids=[sorted_players[0].player_id] if sorted_players else [],
            rankings=[(p.player_id, p.score) for p in sorted_players],
            metadata={"total_rounds": self.current_round},
        )

    async def init_round(self, round_num: int) -> None:
        """Initialize round state"""
        self.phase = GamePhase.DRAWING
        # Rotate drawer
        self.current_drawer_idx = round_num % len(self.players)
        drawer = self.players[self.current_drawer_idx]

        # Pick a word
        if not self.word_pool:
            self.word_pool = DEFAULT_WORDS.copy()
            random.shuffle(self.word_pool)
        self.current_target_word = self.word_pool.pop()
        self.current_description = ""
        self.round_scores = {p.player_id: 0.0 for p in self.players}

        # Update roles
        for i, p in enumerate(self.players):
            p.role = "drawer" if i == self.current_drawer_idx else "guesser"

        logger.info(
            f"Round {round_num} started. Drawer: {drawer.name}, Target: {self.current_target_word}"
        )

    def is_round_over(self) -> bool:
        """Round ends after settlement phase"""
        return self.phase == GamePhase.SETTLEMENT

    async def end_round(self, round_num: int) -> None:
        """Clean up round-level state"""
        logger.info(f"Round {round_num} ended. Scores: {self.round_scores}")

    def get_active_players(self) -> list[str]:
        """Determine which players act in current step"""
        if self.phase == GamePhase.DRAWING:
            # Only the drawer acts
            return [self.players[self.current_drawer_idx].player_id]
        elif self.phase == GamePhase.GUESSING:
            # All guessers act
            return [
                p.player_id
                for i, p in enumerate(self.players)
                if i != self.current_drawer_idx
            ]
        return []

    def is_concurrent_step(self) -> bool:
        """Guessers act concurrently; Drawer acts sequentially"""
        return self.phase == GamePhase.GUESSING

    def build_observation(self, player_id: str) -> Observation:
        """Build private observation for a specific player"""
        player = next(p for p in self.players if p.player_id == player_id)

        if self.phase == GamePhase.DRAWING:
            prompt = DRAWER_ACTION_PROMPT.format(
                target_word=self.current_target_word, num_guessers=len(self.players) - 1
            )
            return Observation(
                round_num=self.current_round,
                step_num=self.current_step,
                player_role="drawer",
                visible_state={"phase": "drawing"},
                action_prompt=prompt,
            )
        else:
            prompt = GUESSER_ACTION_PROMPT.format(description=self.current_description)
            return Observation(
                round_num=self.current_round,
                step_num=self.current_step,
                player_role="guesser",
                visible_state={
                    "phase": "guessing",
                    "description": self.current_description,
                },
                action_prompt=prompt,
            )

    def validate_action(self, player_id: str, action: Action) -> Action:
        """Basic validation of action content"""
        if not action.content:
            action.content = "..."  # Default content to prevent crashes
        return action

    async def apply_actions(self, actions: list[PlayerAction]) -> None:
        """Update game state based on actions"""
        if self.phase == GamePhase.DRAWING:
            if actions:
                self.current_description = actions[0].action.content
                logger.info(
                    f"Drawer provided description: {self.current_description[:50]}..."
                )

        elif self.phase == GamePhase.GUESSING:
            # Process guesses
            correct_count = 0
            drawer_id = self.players[self.current_drawer_idx].player_id

            for pa in actions:
                # Simple exact match (fuzzy matching could be handled by a Referee)
                is_correct = (
                    self.current_target_word.lower() in pa.action.content.lower()
                )
                if is_correct:
                    self.round_scores[pa.player_id] = 1.0
                    self.players_map[pa.player_id].score += 1.0
                    correct_count += 1

            # Scoring for Drawer:
            # 1 point per correct guesser, but 0 if everyone is correct
            num_guessers = len(self.players) - 1
            if 0 < correct_count < num_guessers:
                drawer_score = float(correct_count)
                self.round_scores[drawer_id] = drawer_score
                self.players_map[drawer_id].score += drawer_score
            elif correct_count == num_guessers:
                # All correct - too easy!
                self.round_scores[drawer_id] = 0.0
                logger.info(
                    f"Drawer {drawer_id} got 0 points because everyone guessed correctly."
                )
            else:
                self.round_scores[drawer_id] = 0.0

    def step_transition(self) -> None:
        """Advance game phase"""
        if self.phase == GamePhase.DRAWING:
            self.phase = GamePhase.GUESSING
        elif self.phase == GamePhase.GUESSING:
            self.phase = GamePhase.SETTLEMENT
