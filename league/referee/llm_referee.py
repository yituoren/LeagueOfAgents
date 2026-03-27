"""LLM-based Referee Implementation"""

from __future__ import annotations

import json
import logging
import re

from league.llm.client import LLMClient
from league.referee.base import Referee
from league.types import JudgeContext, JudgeResult

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """\
You are a game referee. You need to determine if each player's answer is correct based on the given target answer and the players' responses.
Judgment Rule: Any response that is semantically consistent with the target is considered correct (synonyms and near-synonymous expressions are acceptable).

Please return the results in JSON format:
{
  "judgements": [
    {"player_id": "...", "correct": true/false, "reason": "..."}
  ]
}
"""


class LLMReferee(Referee):
    """LLM-based Referee

    Uses a Large Language Model for semantic judgment, suitable for fuzzy matching of natural language answers.
    """

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    async def judge(self, context: JudgeContext) -> JudgeResult:
        """Use LLM to determine if players' answers are correct"""
        guesses_text = "\n".join(
            f"- Player {a.player_id}: {a.action.content}" for a in context.actions
        )

        prompt = (
            f"Target Answer: {context.target}\n\n"
            f"Players' Guesses:\n{guesses_text}\n\n"
            f"Please judge the correctness of each guess."
        )

        response = await self.llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            system=JUDGE_SYSTEM_PROMPT,
        )

        # Parse JSON response
        try:
            # Simple JSON extraction from markdown if necessary
            json_match = re.search(r"(\{.*\})", response, re.DOTALL)
            json_str = json_match.group(1) if json_match else response
            data = json.loads(json_str)

            correct_players = []
            scores = {}
            reasoning = ""

            for item in data.get("judgements", []):
                pid = item["player_id"]
                is_correct = item["correct"]
                if is_correct:
                    correct_players.append(pid)
                scores[pid] = 1.0 if is_correct else 0.0
                reasoning += f"{pid}: {item.get('reason', '')}\n"

            return JudgeResult(
                correct_players=correct_players,
                scores=scores,
                reasoning=reasoning.strip(),
            )

        except Exception as e:
            logger.error(f"Error parsing LLM Referee response: {e}. Raw: {response}")
            # Fallback: Treat all as incorrect
            return JudgeResult(
                correct_players=[],
                scores={a.player_id: 0.0 for a in context.actions},
                reasoning=f"Error during judgment: {e}",
            )
