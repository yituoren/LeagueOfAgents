"""你画我猜裁判 - 语义判定"""

from __future__ import annotations

from league.referee.llm_referee import LLMReferee
from league.types import JudgeContext, JudgeResult


class DrawAndGuessReferee(LLMReferee):
    """你画我猜裁判

    基于LLM语义匹配判定猜测是否正确，
    并根据博弈规则计分。
    """

    async def judge(self, context: JudgeContext) -> JudgeResult:
        """判定猜测并计分

        计分规则：
        - 猜对的玩家各得1分
        - 作画者得分 = 猜对人数（若全部猜对则得0分）
        """
        result = await super().judge(context)

        num_guessers = len(context.actions)
        num_correct = len(result.correct_players)
        drawer_id = context.extra.get("drawer_id", "")

        scores: dict[str, float] = {}
        for action in context.actions:
            pid = action.player_id
            scores[pid] = 1.0 if pid in result.correct_players else 0.0

        if drawer_id:
            if num_correct == num_guessers and num_guessers > 0:
                scores[drawer_id] = 0.0  # 全猜对，作画者不得分
            else:
                scores[drawer_id] = float(num_correct)

        result.scores = scores
        return result
