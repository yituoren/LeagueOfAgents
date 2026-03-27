"""Draw and Guess Referee - Semantic Judgment"""

from __future__ import annotations

from league.referee.llm_referee import LLMReferee
from league.types import JudgeContext, JudgeResult


class DrawAndGuessReferee(LLMReferee):
    """Draw and Guess Referee

    Uses LLM semantic matching to determine if a guess is correct,
    and calculates scores based on game theory rules.
    """

    async def judge(self, context: JudgeContext) -> JudgeResult:
        """Judge guesses and calculate scores

        Scoring Rules:
        - Each player who guesses correctly receives 1 point.
        - Drawer's score = Number of correct guessers (if everyone guesses correctly, the drawer receives 0 points).
        """
        # Call base class LLM logic to determine which players are correct
        # The base LLMReferee should return a list of player_ids who matched the target
        result = await super().judge(context)

        drawer_id = context.extra.get("drawer_id")
        scores = {pid: 0.0 for pid in result.scores.keys()}

        # 1 point for each correct guesser
        num_correct = 0
        for pid in result.correct_players:
            scores[pid] = 1.0
            num_correct += 1

        # Calculate drawer score
        num_guessers = len(context.actions)
        if drawer_id:
            if num_correct == num_guessers and num_guessers > 0:
                scores[drawer_id] = 0.0  # Everyone guessed correctly, drawer gets 0
            else:
                scores[drawer_id] = float(num_correct)

        result.scores = scores
        return result
