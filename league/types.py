"""公共类型定义"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PlayerRole(str, Enum):
    """玩家角色枚举（游戏可扩展）"""
    DRAWER = "drawer"
    GUESSER = "guesser"


@dataclass
class Observation:
    """玩家观测信息（信息隔离核心）"""
    round_num: int
    step_num: int
    player_role: str
    visible_state: dict[str, Any]
    action_prompt: str
    available_actions: list[str] | None = None
    history: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Action:
    """玩家动作"""
    action_type: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlayerAction:
    """带玩家ID和时间戳的动作记录"""
    player_id: str
    action: Action
    timestamp: float = field(default_factory=time.time)


@dataclass
class Player:
    """玩家实例"""
    player_id: str
    name: str
    agent: Any  # Agent instance, avoid circular import
    role: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameConfig:
    """游戏配置"""
    num_rounds: int = 1
    max_steps_per_round: int = 100
    timeout_seconds: float = 30.0
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class RoundResult:
    """单轮结果"""
    round_num: int
    scores: dict[str, float] = field(default_factory=dict)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class GameResult:
    """游戏最终结果"""
    round_results: list[RoundResult] = field(default_factory=list)
    final_scores: dict[str, float] = field(default_factory=dict)
    winner: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JudgeContext:
    """裁判判定上下文"""
    round_num: int
    target: str
    actions: list[PlayerAction]
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class JudgeResult:
    """裁判判定结果"""
    correct_players: list[str] = field(default_factory=list)
    scores: dict[str, float] = field(default_factory=dict)
    reasoning: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class LogEvent:
    """日志事件"""
    timestamp: float = field(default_factory=time.time)
    event_type: str = ""
    round_num: int = 0
    step_num: int = 0
    player_id: str = ""
    data: dict[str, Any] = field(default_factory=dict)
