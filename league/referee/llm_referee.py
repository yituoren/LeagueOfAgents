"""LLM裁判实现"""

from __future__ import annotations

import json
import logging

from league.llm.client import LLMClient
from league.referee.base import Referee
from league.types import JudgeContext, JudgeResult

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """\
你是一个游戏裁判。你需要根据给定的目标答案和玩家的回答，判断每个玩家是否回答正确。
判定规则：语义一致即算正确（同义词、近义表达均可）。

请以JSON格式返回结果：
{
  "judgements": [
    {"player_id": "...", "correct": true/false, "reason": "..."}
  ]
}
"""


class LLMReferee(Referee):
    """基于LLM的裁判

    使用大模型进行语义判定，适用于自然语言答案的模糊匹配场景。
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    async def judge(self, context: JudgeContext) -> JudgeResult:
        """使用LLM判定玩家回答是否正确"""
        guesses_text = "\n".join(
            f"- 玩家 {a.player_id}: {a.action.content}"
            for a in context.actions
        )
        prompt = (
            f"目标答案: {context.target}\n\n"
            f"玩家回答:\n{guesses_text}\n\n"
            "请判定每个玩家的回答是否与目标答案语义一致。"
        )

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            system=JUDGE_SYSTEM_PROMPT,
        )

        return self._parse_response(response, context)

    def _parse_response(
        self, response: str, context: JudgeContext
    ) -> JudgeResult:
        """解析LLM裁判响应"""
        correct_players: list[str] = []
        reasoning_parts: list[str] = []

        try:
            # 尝试提取JSON
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(response[start:end])
                for item in data.get("judgements", []):
                    pid = item["player_id"]
                    if item.get("correct", False):
                        correct_players.append(pid)
                    reasoning_parts.append(
                        f"{pid}: {'correct' if item.get('correct') else 'wrong'}"
                        f" - {item.get('reason', '')}"
                    )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse referee response: %s", e)
            reasoning_parts.append(f"Parse error: {e}")

        return JudgeResult(
            correct_players=correct_players,
            reasoning="; ".join(reasoning_parts),
        )
