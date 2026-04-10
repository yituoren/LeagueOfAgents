"""Dou Dizhu card combo parsing and comparison.

Cards are represented as string ranks (suits don't matter in Dou Dizhu):
  "3","4","5","6","7","8","9","10","J","Q","K","A","2","SJ","BJ"
SJ = small joker (小王), BJ = big joker (大王).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

RANK_VALUES: dict[str, int] = {
    "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10,
    "J": 11, "Q": 12, "K": 13, "A": 14, "2": 15, "SJ": 16, "BJ": 17,
}

# Ranks allowed in sequential combos (straights, pair-straights, planes)
# Excludes 2 and jokers.
MAX_SEQUENTIAL_RANK = 14  # A


def create_deck() -> list[str]:
    """Create a standard 54-card Dou Dizhu deck."""
    deck: list[str] = []
    for rank in ["3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A", "2"]:
        deck.extend([rank] * 4)
    deck.extend(["SJ", "BJ"])
    return deck


def sort_cards(cards: list[str]) -> list[str]:
    """Sort cards ascending by rank."""
    return sorted(cards, key=lambda c: RANK_VALUES[c])


class ComboType(Enum):
    SINGLE = "single"
    PAIR = "pair"
    TRIPLE = "triple"
    TRIPLE_SINGLE = "triple+1"
    TRIPLE_PAIR = "triple+2"
    STRAIGHT = "straight"
    PAIR_STRAIGHT = "pair_straight"
    PLANE = "plane"
    PLANE_SINGLES = "plane+singles"
    PLANE_PAIRS = "plane+pairs"
    FOUR_TWO_SINGLES = "four+2"
    FOUR_TWO_PAIRS = "four+2pairs"
    BOMB = "bomb"
    ROCKET = "rocket"
    INVALID = "invalid"


@dataclass
class Combo:
    type: ComboType
    main_rank: int  # Primary rank for comparison
    length: int     # Number of "groups" (e.g., straight length, plane triples)
    size: int       # Total card count
    cards: list[str]

    @property
    def is_bomb_like(self) -> bool:
        return self.type in (ComboType.BOMB, ComboType.ROCKET)


def _is_consecutive(ranks: list[int]) -> bool:
    if len(ranks) < 2:
        return True
    return all(ranks[i] == ranks[i - 1] + 1 for i in range(1, len(ranks)))


def parse_combo(cards: list[str]) -> Combo:
    """Parse a list of cards into a Combo, or ComboType.INVALID."""
    if not cards:
        return Combo(ComboType.INVALID, 0, 0, 0, cards)

    counts: dict[int, int] = {}
    for c in cards:
        if c not in RANK_VALUES:
            return Combo(ComboType.INVALID, 0, 0, 0, cards)
        r = RANK_VALUES[c]
        counts[r] = counts.get(r, 0) + 1

    n = len(cards)
    count_values = sorted(counts.values(), reverse=True)
    ranks = sorted(counts.keys())

    # Rocket
    if n == 2 and set(cards) == {"SJ", "BJ"}:
        return Combo(ComboType.ROCKET, 17, 1, 2, cards)

    # Bomb
    if n == 4 and count_values == [4]:
        return Combo(ComboType.BOMB, ranks[0], 1, 4, cards)

    # Single
    if n == 1:
        return Combo(ComboType.SINGLE, ranks[0], 1, 1, cards)

    # Pair
    if n == 2 and count_values == [2]:
        return Combo(ComboType.PAIR, ranks[0], 1, 2, cards)

    # Triple
    if n == 3 and count_values == [3]:
        return Combo(ComboType.TRIPLE, ranks[0], 1, 3, cards)

    # Triple + single
    if n == 4 and count_values == [3, 1]:
        triple_rank = next(r for r, c in counts.items() if c == 3)
        return Combo(ComboType.TRIPLE_SINGLE, triple_rank, 1, 4, cards)

    # Triple + pair
    if n == 5 and count_values == [3, 2]:
        triple_rank = next(r for r, c in counts.items() if c == 3)
        return Combo(ComboType.TRIPLE_PAIR, triple_rank, 1, 5, cards)

    # Four + 2 singles
    if n == 6 and count_values == [4, 1, 1]:
        four_rank = next(r for r, c in counts.items() if c == 4)
        return Combo(ComboType.FOUR_TWO_SINGLES, four_rank, 1, 6, cards)

    # Four + 2 pairs
    if n == 8 and count_values == [4, 2, 2]:
        four_rank = next(r for r, c in counts.items() if c == 4)
        return Combo(ComboType.FOUR_TWO_PAIRS, four_rank, 1, 8, cards)

    # Straight (5+ consecutive, no 2/jokers)
    if n >= 5 and all(c == 1 for c in counts.values()):
        if _is_consecutive(ranks) and max(ranks) <= MAX_SEQUENTIAL_RANK:
            return Combo(ComboType.STRAIGHT, min(ranks), n, n, cards)

    # Pair straight (3+ consecutive pairs)
    if n >= 6 and n % 2 == 0 and all(c == 2 for c in counts.values()):
        if _is_consecutive(ranks) and max(ranks) <= MAX_SEQUENTIAL_RANK:
            return Combo(ComboType.PAIR_STRAIGHT, min(ranks), len(ranks), n, cards)

    # Pure plane (2+ consecutive triples)
    if n >= 6 and n % 3 == 0 and all(c == 3 for c in counts.values()):
        if _is_consecutive(ranks) and max(ranks) <= MAX_SEQUENTIAL_RANK:
            return Combo(ComboType.PLANE, min(ranks), len(ranks), n, cards)

    # Plane with wings (singles or pairs)
    triple_ranks_sorted = sorted(r for r, c in counts.items() if c >= 3 and r <= MAX_SEQUENTIAL_RANK)
    for plane_len in range(len(triple_ranks_sorted), 1, -1):
        for start in range(len(triple_ranks_sorted) - plane_len + 1):
            plane_part = triple_ranks_sorted[start:start + plane_len]
            if not _is_consecutive(plane_part):
                continue

            # Plane + singles: 4 cards per "group" (triple + 1)
            if n == 4 * plane_len:
                remaining = dict(counts)
                for r in plane_part:
                    remaining[r] -= 3
                    if remaining[r] == 0:
                        del remaining[r]
                # Wings must all be singles, total == plane_len
                if sum(remaining.values()) == plane_len and all(c == 1 for c in remaining.values()):
                    return Combo(ComboType.PLANE_SINGLES, min(plane_part), plane_len, n, cards)

            # Plane + pairs: 5 cards per "group" (triple + 2)
            if n == 5 * plane_len:
                remaining = dict(counts)
                for r in plane_part:
                    remaining[r] -= 3
                    if remaining[r] == 0:
                        del remaining[r]
                if len(remaining) == plane_len and all(c == 2 for c in remaining.values()):
                    return Combo(ComboType.PLANE_PAIRS, min(plane_part), plane_len, n, cards)

    return Combo(ComboType.INVALID, 0, 0, 0, cards)


def can_beat(new: Combo, prev: Combo) -> bool:
    """Check if `new` combo can legally beat `prev` combo."""
    if new.type == ComboType.INVALID:
        return False
    if prev.type == ComboType.INVALID or prev.size == 0:
        return True  # Leading, any valid combo

    # Rocket beats everything
    if new.type == ComboType.ROCKET:
        return True
    if prev.type == ComboType.ROCKET:
        return False

    # Bomb beats non-bombs; higher bomb beats lower
    if new.type == ComboType.BOMB:
        if prev.type == ComboType.BOMB:
            return new.main_rank > prev.main_rank
        return True
    if prev.type == ComboType.BOMB:
        return False

    # Same shape required
    if new.type != prev.type or new.size != prev.size or new.length != prev.length:
        return False
    return new.main_rank > prev.main_rank
