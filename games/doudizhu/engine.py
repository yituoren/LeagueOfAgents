"""Dou Dizhu Game Engine."""

from __future__ import annotations

import logging
import random
from enum import Enum

from games.doudizhu.prompts import (
    BID_PROMPT,
    DOUDIZHU_SYSTEM_PROMPT,
    PLAY_PROMPT,
)
from games.doudizhu.rules import (
    RANK_VALUES,
    Combo,
    ComboType,
    can_beat,
    create_deck,
    parse_combo,
    sort_cards,
)
from league.engine.base import GameEngine
from league.logger.game_logger import GameLogger
from league.prompts.agent import AGENT_BASE_PROMPT
from league.types import (
    Action,
    GameResult,
    Observation,
    PlayerAction,
)

logger = logging.getLogger(__name__)


class Phase(Enum):
    BIDDING = "bidding"
    PLAYING = "playing"
    SETTLEMENT = "settlement"


class DouDizhuEngine(GameEngine):
    """Dou Dizhu (Fight the Landlord) — 3 players, 1 landlord vs 2 peasants.

    Round structure:
      - [BIDDING steps] each player bids 0–3 in turn; highest becomes landlord.
      - [PLAYING steps] landlord plays first; turns rotate. Winner = first empty hand.
      - [SETTLEMENT] base × multiplier × 2^bombs → landlord ±2x, peasants ∓1x.
    """

    BASE_SCORE = 1

    def __init__(self, game_logger: GameLogger | None = None) -> None:
        super().__init__(game_logger)
        self.phase = Phase.BIDDING
        self.hands: dict[str, list[str]] = {}
        self.landlord_cards: list[str] = []
        self.bids: dict[str, int] = {}
        self.current_bid_idx: int = 0
        self.landlord_id: str | None = None
        self.multiplier: int = 1
        self.bomb_count: int = 0
        self.current_turn_idx: int = 0
        self.last_combo: Combo | None = None
        self.last_player_id: str | None = None
        self.play_history: list[dict] = []
        self.winner_id: str | None = None

    # ========== Game Layer ==========

    async def on_game_start(self) -> None:
        if len(self.players) != 3:
            raise ValueError(
                f"Dou Dizhu requires exactly 3 players, got {len(self.players)}"
            )

        # Inject game-specific system prompt into all agents
        full_prompt = f"{AGENT_BASE_PROMPT}\n---\n\n{DOUDIZHU_SYSTEM_PROMPT}"
        for p in self.players:
            if hasattr(p.agent, "system_prompt"):
                p.agent.system_prompt = full_prompt

        logger.info(
            f"Dou Dizhu started: {', '.join(p.name for p in self.players)} | "
            f"{self.config.num_rounds} rounds"
        )

    def is_game_over(self) -> bool:
        return self.current_round >= self.config.num_rounds

    def get_results(self) -> GameResult:
        sorted_players = sorted(self.players, key=lambda p: p.score, reverse=True)
        return GameResult(
            winner_ids=[sorted_players[0].player_id] if sorted_players else [],
            rankings=[(p.player_id, p.score) for p in sorted_players],
            metadata={"total_rounds": self.current_round},
        )

    # ========== Round Layer ==========

    async def init_round(self, round_num: int) -> None:
        deck = create_deck()
        random.shuffle(deck)

        self.hands = {
            p.player_id: sort_cards(deck[i * 17 : (i + 1) * 17])
            for i, p in enumerate(self.players)
        }
        self.landlord_cards = deck[51:54]

        self.phase = Phase.BIDDING
        self.bids = {}
        self.current_bid_idx = 0
        self.landlord_id = None
        self.multiplier = 1
        self.bomb_count = 0
        self.current_turn_idx = 0
        self.last_combo = None
        self.last_player_id = None
        self.play_history = []
        self.winner_id = None

        logger.info(f"=== Round {round_num} ===")
        for p in self.players:
            logger.info(f"  {p.name}: {' '.join(self.hands[p.player_id])}")
        logger.info(f"  Landlord cards: {' '.join(self.landlord_cards)}")

    def is_round_over(self) -> bool:
        return self.phase == Phase.SETTLEMENT

    async def end_round(self, round_num: int) -> None:
        if self.landlord_id is None:
            logger.info(f"Round {round_num} ended with no landlord")
            return

        base = self.BASE_SCORE * self.multiplier * (2**self.bomb_count)
        landlord_won = self.winner_id == self.landlord_id

        for p in self.players:
            if p.player_id == self.landlord_id:
                p.score += 2 * base if landlord_won else -2 * base
            else:
                p.score += -base if landlord_won else base

        landlord = self.players_map[self.landlord_id]
        winner = self.players_map[self.winner_id] if self.winner_id else None
        logger.info(
            f"Round {round_num} over. Landlord={landlord.name} "
            f"{'WON' if landlord_won else 'LOST'}. "
            f"Winner={winner.name if winner else '?'}. "
            f"base={base} (mult={self.multiplier}, bombs={self.bomb_count})"
        )
        logger.info(f"Scores: {[(p.name, p.score) for p in self.players]}")

    # ========== Step Layer ==========

    def get_active_players(self) -> list[str]:
        if self.phase == Phase.BIDDING:
            if self.current_bid_idx < len(self.players):
                return [self.players[self.current_bid_idx].player_id]
            return []
        if self.phase == Phase.PLAYING:
            return [self.players[self.current_turn_idx].player_id]
        return []

    def is_concurrent_step(self) -> bool:
        return False

    def build_observation(self, player_id: str) -> Observation:
        player = self.players_map[player_id]
        hand = self.hands[player_id]

        if self.phase == Phase.BIDDING:
            prompt = BID_PROMPT.format(
                round_num=self.current_round,
                num_cards=len(hand),
                hand=" ".join(hand),
                bids_so_far=self._format_bids(),
            )
            return Observation(
                round_num=self.current_round,
                step_num=self.current_step,
                player_role="bidder",
                visible_state={
                    "phase": "bidding",
                    "hand": list(hand),
                    "bids": dict(self.bids),
                },
                action_prompt=prompt,
            )

        # PLAYING
        is_landlord = player_id == self.landlord_id
        role = "landlord" if is_landlord else "peasant"
        must_lead = self.last_combo is None or self.last_player_id == player_id

        if must_lead:
            lead_notice = "**You have control — lead with any valid combo.**"
            instruction = "Choose the best combo to play from your hand."
        else:
            lead_notice = "You must beat the last play with the same combo type (higher rank) or use a bomb/rocket — or pass."
            instruction = "Play a combo that beats the last play, or pass."

        prompt = PLAY_PROMPT.format(
            round_num=self.current_round,
            player_name=player.name,
            role=role,
            landlord_name=self.players_map[self.landlord_id].name
            if self.landlord_id
            else "?",
            hand_sizes=self._format_hand_sizes(),
            history=self._format_history(),
            last_play=self._format_last_play(),
            lead_notice=lead_notice,
            num_cards=len(hand),
            hand=" ".join(hand),
            instruction=instruction,
        )

        return Observation(
            round_num=self.current_round,
            step_num=self.current_step,
            player_role=role,
            visible_state={
                "phase": "playing",
                "hand": list(hand),
                "last_combo": list(self.last_combo.cards) if self.last_combo else None,
                "last_player_id": self.last_player_id,
                "must_lead": must_lead,
            },
            action_prompt=prompt,
        )

    def validate_action(self, player_id: str, action: Action) -> Action:
        return action

    async def apply_actions(self, actions: list[PlayerAction]) -> None:
        if not actions:
            return
        if self.phase == Phase.BIDDING:
            self._apply_bid(actions[0])
        elif self.phase == Phase.PLAYING:
            self._apply_play(actions[0])

    def step_transition(self) -> None:
        # Bidding complete → PLAYING
        if self.phase == Phase.BIDDING and self.landlord_id is not None:
            self.phase = Phase.PLAYING
        # PLAYING → SETTLEMENT is set directly in _apply_play when a hand empties

    # ========== Bidding Logic ==========

    def _apply_bid(self, pa: PlayerAction) -> None:
        bid = self._parse_bid(pa.action.content)
        self.bids[pa.player_id] = bid
        logger.info(f"{self.players_map[pa.player_id].name} bids {bid}")
        self.current_bid_idx += 1

        if self.current_bid_idx >= len(self.players):
            self._finalize_landlord()

    def _finalize_landlord(self) -> None:
        max_bid = max(self.bids.values())
        if max_bid == 0:
            # Nobody bid — assign first player as landlord with multiplier 1
            self.landlord_id = self.players[0].player_id
            self.multiplier = 1
        else:
            for p in self.players:
                if self.bids[p.player_id] == max_bid:
                    self.landlord_id = p.player_id
                    self.multiplier = max_bid
                    break

        # Landlord receives the 3 hidden cards
        assert self.landlord_id is not None
        self.hands[self.landlord_id] = sort_cards(
            self.hands[self.landlord_id] + self.landlord_cards
        )

        # Landlord plays first
        for i, p in enumerate(self.players):
            if p.player_id == self.landlord_id:
                self.current_turn_idx = i
                break

        landlord = self.players_map[self.landlord_id]
        logger.info(
            f"Landlord: {landlord.name} (multiplier={self.multiplier}). "
            f"Hand: {' '.join(self.hands[self.landlord_id])}"
        )

    def _parse_bid(self, content: str) -> int:
        """Strict parse: content must be exactly '0', '1', '2', or '3'."""
        text = content.strip()
        if text in ("0", "1", "2", "3"):
            return int(text)
        logger.error(f"Invalid bid output {content!r} — treating as 0 (pass)")
        return 0

    # ========== Playing Logic ==========

    def _apply_play(self, pa: PlayerAction) -> None:
        player_id = pa.player_id
        player_name = self.players_map[player_id].name
        hand = self.hands[player_id]
        must_lead = self.last_combo is None or self.last_player_id == player_id

        parsed = self._parse_play(pa.action.content)

        if parsed is None:
            # Malformed output — forfeit this turn
            logger.error(
                f"{player_name} produced malformed output {pa.action.content!r} "
                "— forfeiting turn"
            )
            self._record_pass(player_id)
            self._advance_turn()
            return

        cards, is_pass = parsed

        if is_pass:
            if must_lead:
                logger.error(
                    f"{player_name} illegally passed while leading — forfeiting turn"
                )
            self._record_pass(player_id)
            logger.info(f"{player_name} passes")
            self._advance_turn()
            return

        # Cards must exist in hand
        if not self._has_cards(hand, cards):
            logger.error(
                f"{player_name} played cards not in hand: {cards} (hand: {hand}) — forfeiting turn"
            )
            self._record_pass(player_id)
            self._advance_turn()
            return

        combo = parse_combo(cards)
        if combo.type == ComboType.INVALID:
            logger.error(
                f"{player_name} played invalid combo {cards} — forfeiting turn"
            )
            self._record_pass(player_id)
            self._advance_turn()
            return

        # Must beat previous play if not leading
        if not must_lead and not can_beat(combo, self.last_combo):  # type: ignore[arg-type]
            logger.error(
                f"{player_name}'s {combo.type.value} {cards} can't beat "
                f"{self.last_combo.type.value} {self.last_combo.cards} — forfeiting turn"  # type: ignore[union-attr]
            )
            self._record_pass(player_id)
            self._advance_turn()
            return

        # Commit the play
        for c in cards:
            hand.remove(c)
        self.last_combo = combo
        self.last_player_id = player_id
        if combo.is_bomb_like:
            self.bomb_count += 1
        self.play_history.append(
            {
                "player_id": player_id,
                "cards": list(cards),
                "combo_type": combo.type.value,
                "pass": False,
            }
        )
        logger.info(
            f"{player_name} plays: {' '.join(cards)} ({combo.type.value}) | "
            f"hand: [{' '.join(hand) if hand else 'empty'}]"
        )

        if not hand:
            self.winner_id = player_id
            self.phase = Phase.SETTLEMENT
            return

        self._advance_turn()

    def _record_pass(self, player_id: str) -> None:
        self.play_history.append(
            {
                "player_id": player_id,
                "cards": [],
                "combo_type": "pass",
                "pass": True,
            }
        )

    def _advance_turn(self) -> None:
        self.current_turn_idx = (self.current_turn_idx + 1) % len(self.players)

    @staticmethod
    def _has_cards(hand: list[str], cards: list[str]) -> bool:
        from collections import Counter

        return not (Counter(cards) - Counter(hand))

    @staticmethod
    def _parse_play(content: str) -> tuple[list[str], bool] | None:
        """Strict parse of LLM play output.

        Accepted formats only:
          - `pass` (case-insensitive, no surrounding text)
          - Whitespace-separated card tokens from the canonical set:
            "3"-"10", "J", "Q", "K", "A", "2", "SJ", "BJ" (case-sensitive)

        Returns:
          ([], True)       → pass
          (cards, False)   → play these cards
          None             → malformed; caller should forfeit the turn
        """
        text = content.strip()
        if text.lower() == "pass":
            return [], True
        tokens = text.split()
        if not tokens:
            return None
        for tok in tokens:
            if tok not in RANK_VALUES:
                return None
        return list(tokens), False

    # ========== Formatting Helpers ==========

    def _format_bids(self) -> str:
        if not self.bids:
            return "(none yet — you are first)"
        return ", ".join(
            f"{self.players_map[pid].name}={bid}" for pid, bid in self.bids.items()
        )

    def _format_last_play(self) -> str:
        if self.last_combo is None or self.last_player_id is None:
            return "(none — you lead)"
        name = self.players_map[self.last_player_id].name
        return f"{name} played [{' '.join(self.last_combo.cards)}] ({self.last_combo.type.value})"

    def _format_history(self) -> str:
        """Show only the last 2 turns of the current round (information limit)."""
        if not self.play_history:
            return "  (no plays yet this round)"
        lines = []
        for h in self.play_history[-2:]:
            name = self.players_map[h["player_id"]].name
            role = "L" if h["player_id"] == self.landlord_id else "P"
            if h["pass"]:
                lines.append(f"  {name}({role}): pass")
            else:
                lines.append(
                    f"  {name}({role}): {' '.join(h['cards'])}  [{h['combo_type']}]"
                )
        return "\n".join(lines)

    def _format_hand_sizes(self) -> str:
        parts = []
        for p in self.players:
            role = "landlord" if p.player_id == self.landlord_id else "peasant"
            parts.append(f"{p.name}({role})={len(self.hands[p.player_id])}")
        return ", ".join(parts)
