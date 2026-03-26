"""你画我猜游戏引擎"""

from __future__ import annotations

import logging
import random
from enum import Enum

from league.engine.base import GameEngine
from league.logger.game_logger import GameLogger
from league.types import (
    Action,
    GameConfig,
    GameResult,
    JudgeContext,
    Observation,
    Player,
    PlayerAction,
    RoundResult,
)
from games.draw_and_guess.prompts import DRAWER_ACTION_PROMPT, GUESSER_ACTION_PROMPT
from games.draw_and_guess.referee import DrawAndGuessReferee

logger = logging.getLogger(__name__)

# 默认词库
DEFAULT_WORDS = [
    "苹果", "太阳", "月亮", "猫", "飞机",
    "雪花", "吉他", "城堡", "彩虹", "机器人",
    "火山", "钻石", "蝴蝶", "望远镜", "灯塔",
]


class RoundPhase(str, Enum):
    DRAWING = "drawing"
    GUESSING = "guessing"
    JUDGING = "judging"
    FINISHED = "finished"


class DrawAndGuessEngine(GameEngine):
    """你画我猜游戏引擎

    Game: N轮（每人轮流当作画者）
      Round (玩家X作画):
        Step 1 [sequential]: query 作画者 -> 返回画作描述
        Step 2 [concurrent]: query 猜词者 -> 同时猜词
        Step 3 [engine内部]: referee判定 + 计分
    """

    def __init__(self, referee: DrawAndGuessReferee) -> None:
        super().__init__()
        self.referee = referee
        self.game_logger = GameLogger(game_name="draw_and_guess")
        self.word_pool: list[str] = list(DEFAULT_WORDS)

        # Round state
        self.drawer_id: str = ""
        self.guesser_ids: list[str] = []
        self.target_word: str = ""
        self.drawing_description: str = ""
        self.phase: RoundPhase = RoundPhase.FINISHED
        self.player_order: list[str] = []
        self.round_results: list[RoundResult] = []

    # ========== Game 层 ==========

    async def on_game_start(self) -> None:
        self.player_order = list(self.players.keys())
        random.shuffle(self.player_order)
        for p in self.players.values():
            p.score = 0.0
            p.agent.reset()
        self.round_results = []
        self.game_logger.log_event(
            "game_start",
            data={"players": self.player_order},
        )

    def is_game_over(self) -> bool:
        return self.current_round >= self.config.num_rounds

    def get_results(self) -> GameResult:
        final_scores = {pid: p.score for pid, p in self.players.items()}
        winner = max(final_scores, key=final_scores.get) if final_scores else None  # type: ignore[arg-type]
        self.game_logger.log_event(
            "game_end", data={"final_scores": final_scores, "winner": winner}
        )
        return GameResult(
            round_results=self.round_results,
            final_scores=final_scores,
            winner=winner,
        )

    # ========== Round 层 ==========

    async def init_round(self, round_num: int) -> None:
        drawer_idx = round_num % len(self.player_order)
        self.drawer_id = self.player_order[drawer_idx]
        self.guesser_ids = [
            pid for pid in self.player_order if pid != self.drawer_id
        ]
        self.target_word = random.choice(self.word_pool)
        self.drawing_description = ""
        self.phase = RoundPhase.DRAWING

        self.game_logger.log_event(
            "round_start",
            round_num=round_num,
            data={
                "drawer": self.drawer_id,
                "target_word": self.target_word,
            },
        )
        logger.info(
            "Round %d: drawer=%s, word=%s",
            round_num, self.drawer_id, self.target_word,
        )

    def is_round_over(self) -> bool:
        return self.phase == RoundPhase.FINISHED

    async def end_round(self, round_num: int) -> None:
        self.game_logger.log_event(
            "round_end",
            round_num=round_num,
            data={"phase": self.phase.value},
        )

    # ========== Step 层 ==========

    def get_active_players(self) -> list[str]:
        if self.phase == RoundPhase.DRAWING:
            return [self.drawer_id]
        elif self.phase == RoundPhase.GUESSING:
            return self.guesser_ids
        return []

    def is_concurrent_step(self) -> bool:
        return self.phase == RoundPhase.GUESSING

    def build_observation(self, player_id: str) -> Observation:
        if self.phase == RoundPhase.DRAWING:
            return Observation(
                round_num=self.current_round,
                step_num=self.current_step,
                player_role="drawer",
                visible_state={"num_guessers": len(self.guesser_ids)},
                action_prompt=DRAWER_ACTION_PROMPT.format(
                    target_word=self.target_word,
                    num_guessers=len(self.guesser_ids),
                ),
            )
        else:
            return Observation(
                round_num=self.current_round,
                step_num=self.current_step,
                player_role="guesser",
                visible_state={"description": self.drawing_description},
                action_prompt=GUESSER_ACTION_PROMPT.format(
                    description=self.drawing_description,
                ),
            )

    def validate_action(self, player_id: str, action: Action) -> Action:
        if not action.content.strip():
            action.content = "(empty)"
        return action

    async def apply_actions(self, actions: list[PlayerAction]) -> None:
        if self.phase == RoundPhase.DRAWING:
            if actions:
                self.drawing_description = actions[0].action.content
                self.game_logger.log_action(
                    actions[0], self.current_round, self.current_step
                )

        elif self.phase == RoundPhase.GUESSING:
            for a in actions:
                self.game_logger.log_action(
                    a, self.current_round, self.current_step
                )

            # 裁判判定
            judge_ctx = JudgeContext(
                round_num=self.current_round,
                target=self.target_word,
                actions=actions,
                extra={"drawer_id": self.drawer_id},
            )
            result = await self.referee.judge(judge_ctx)

            # 更新分数
            for pid, score in result.scores.items():
                if pid in self.players:
                    self.players[pid].score += score

            self.round_results.append(RoundResult(
                round_num=self.current_round,
                scores=result.scores,
                details={
                    "target": self.target_word,
                    "drawer": self.drawer_id,
                    "correct_players": result.correct_players,
                    "reasoning": result.reasoning,
                },
            ))

            self.game_logger.log_event(
                "judge_result",
                round_num=self.current_round,
                data={
                    "correct": result.correct_players,
                    "scores": result.scores,
                },
            )

    def step_transition(self) -> None:
        if self.phase == RoundPhase.DRAWING:
            self.phase = RoundPhase.GUESSING
        elif self.phase == RoundPhase.GUESSING:
            self.phase = RoundPhase.FINISHED
