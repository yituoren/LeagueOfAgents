"""Game Log Recording"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from league.types import PlayerAction


class GameLogger:
    """Game Logger

    Records all events and player actions during a game, supporting export to JSON.
    """

    def __init__(self, game_name: str = "game") -> None:
        self.game_name = game_name
        self.start_time = time.time()
        self.logs: list[dict[str, Any]] = []

    def log_event(
        self,
        event_type: str,
        round_num: int = 0,
        step_num: int = 0,
        player_id: str | None = None,
        data: Any = None,
    ) -> None:
        """Log a generic game event"""
        entry = {
            "type": "event",
            "event_type": event_type,
            "timestamp": time.time(),
            "round": round_num,
            "step": step_num,
            "player_id": player_id,
            "data": data,
        }
        self.logs.append(entry)

    def log_action(
        self, action: PlayerAction, round_num: int = 0, step_num: int = 0
    ) -> None:
        """Log a specific player action"""
        entry = {
            "type": "action",
            "player_id": action.player_id,
            "timestamp": action.timestamp,
            "round": round_num,
            "step": step_num,
            "action_type": action.action.action_type,
            "content": action.action.content,
            "metadata": action.action.metadata,
        }
        self.logs.append(entry)

    def export(self, output_path: str | Path | None = None) -> str:
        """Export logs as a JSON string and optionally save to a file"""
        result = {
            "game_name": self.game_name,
            "start_time": self.start_time,
            "end_time": time.time(),
            "logs": self.logs,
        }
        json_str = json.dumps(result, indent=2, ensure_ascii=False)

        if output_path:
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json_str, encoding="utf-8")

        return json_str

    def clear(self) -> None:
        """Clear the current log buffer"""
        self.logs = []
        self.start_time = time.time()
