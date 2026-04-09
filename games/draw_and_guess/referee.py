"""Draw and Guess Referee - Semantic Judgment"""

from __future__ import annotations

import json
import random
import re

from games.draw_and_guess.prompts import REFEREE_TARGET_SELECTION_PROMPT
from league.referee.llm_referee import LLMReferee
from league.types import JudgeContext, JudgeResult


class DrawAndGuessReferee(LLMReferee):
    """Draw and Guess Referee

    Uses LLM semantic matching to determine if a guess is correct,
    and calculates scores based on game theory rules.
    """

    def __init__(self, llm_client) -> None:
        super().__init__(llm_client)
        self.used_targets: list[str] = []
        self._used_targets_norm: set[str] = set()

    def reset_target_history(self) -> None:
        """Reset generated target history for a new game."""
        self.used_targets.clear()
        self._used_targets_norm.clear()

    async def choose_target(
        self,
        round_num: int,
        drawer_name: str,
    ) -> str:
        """Use referee LLM to generate a target word."""
        used_text = ", ".join(self.used_targets) if self.used_targets else "(none)"
        prompt_base = (
            f"Round: {round_num}\n"
            f"Drawer: {drawer_name}\n"
            f"Previously used targets (DO NOT reuse): {used_text}\n"
            "Hard constraint: the new target must be different from all previously used targets.\n"
        )

        last_candidate = ""
        for attempt in range(3):
            prompt = prompt_base + "Generate one target word now."
            if attempt > 0:
                prompt += (
                    f"\nYour previous candidate '{last_candidate}' was invalid or repeated. "
                    "Return a different, unused target."
                )

            response = await self.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                system=REFEREE_TARGET_SELECTION_PROMPT,
                temperature=0.2,
            )

            output_match = re.search(r"<output>(.*?)</output>", response, re.DOTALL)
            json_source = output_match.group(1) if output_match else response

            try:
                json_match = re.search(r"(\{.*\})", json_source, re.DOTALL)
                json_str = json_match.group(1) if json_match else json_source
                data = json.loads(json_str)
                target = str(data.get("target", "")).strip()
                target = re.sub(r"\s+", " ", target).strip()
                last_candidate = target
                if not target:
                    continue

                target_norm = target.lower()
                if target_norm in self._used_targets_norm:
                    continue

                self.used_targets.append(target)
                self._used_targets_norm.add(target_norm)
                return target
            except Exception:
                continue

        # Safe fallback when model output is invalid/repeated
        fallback_pool = ["apple", "cat", "guitar", "castle", "rainbow", "anchor", "telescope"]
        for candidate in fallback_pool:
            candidate_norm = candidate.lower()
            if candidate_norm not in self._used_targets_norm:
                self.used_targets.append(candidate)
                self._used_targets_norm.add(candidate_norm)
                return candidate

        candidate = random.choice(fallback_pool)
        self.used_targets.append(candidate)
        self._used_targets_norm.add(candidate.lower())
        return candidate

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
