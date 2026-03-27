"""Common type definitions"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlayerRole(str, Enum):
    """Player roles enumeration (extensible)"""

    DRAWER = "drawer"
    GUESSER = "guesser"


@dataclass
class Observation:
    """Player observation information (core of information isolation)"""

    round_num: int
    step_num: int
    player_role: str
    visible_state: dict[str, Any]
    action_prompt: str
    available_actions: list[str] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Action:
    """Player action"""

    action_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlayerAction:
    """Action record with player ID and timestamp"""

    player_id: str
    action: Action
    timestamp: float = field(default_factory=time.time)


@dataclass
class Player:
    """Player instance"""

    player_id: str
    name: str
    agent: Any  # Agent instance, avoid circular import
    role: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameConfig:
    """Game configuration"""

    num_rounds: int = 1
    max_steps_per_round: int = 100
    timeout_seconds: float = 30.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoundResult:
    """Result of a single round"""

    round_num: int
    scores: dict[str, float]
    winner_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameResult:
    """Final game result"""

    winner_ids: list[str]
    rankings: list[tuple[str, float]]  # List of (player_id, score)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JudgeContext:
    """Input for referee judgment"""

    round_num: int
    target: str
    actions: list[PlayerAction]
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class JudgeResult:
    """Output of referee judgment"""

    correct_players: list[str]
    scores: dict[str, float]
    reasoning: str = ""


@dataclass
class LogEvent:
    """Generic log event"""

    timestamp: float
    event_type: str
    round_num: int = 0
    step_num: int = 0
    player_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
