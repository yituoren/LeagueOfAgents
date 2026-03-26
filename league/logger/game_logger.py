"""对局日志记录"""

from __future__ import annotations

import json
import time
from pathlib import Path

from league.types import LogEvent, PlayerAction


class GameLogger:
    """游戏日志记录器

    记录对局全过程，支持导出为JSON。
    """

    def __init__(self, game_name: str = "") -> None:
        self.game_name = game_name
        self.events: list[LogEvent] = []

    def log_event(
        self,
        event_type: str,
        round_num: int = 0,
        step_num: int = 0,
        player_id: str = "",
        data: dict | None = None,
    ) -> None:
        """记录一个事件"""
        self.events.append(LogEvent(
            timestamp=time.time(),
            event_type=event_type,
            round_num=round_num,
            step_num=step_num,
            player_id=player_id,
            data=data or {},
        ))

    def log_action(
        self, action: PlayerAction, round_num: int = 0, step_num: int = 0
    ) -> None:
        """记录玩家动作"""
        self.log_event(
            event_type="player_action",
            round_num=round_num,
            step_num=step_num,
            player_id=action.player_id,
            data={
                "action_type": action.action.action_type,
                "content": action.action.content,
                "timestamp": action.timestamp,
            },
        )

    def export(self, output_path: str | Path | None = None) -> str:
        """导出日志为JSON"""
        data = {
            "game_name": self.game_name,
            "total_events": len(self.events),
            "events": [
                {
                    "timestamp": e.timestamp,
                    "event_type": e.event_type,
                    "round_num": e.round_num,
                    "step_num": e.step_num,
                    "player_id": e.player_id,
                    "data": e.data,
                }
                for e in self.events
            ],
        }
        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        if output_path:
            Path(output_path).write_text(json_str, encoding="utf-8")
        return json_str

    def clear(self) -> None:
        """清空日志"""
        self.events.clear()
