"""League of Agents - CLI Entry Point"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import yaml

from games.draw_and_guess.engine import DrawAndGuessEngine
from games.draw_and_guess.tools import ImageGenerationTool
from league.agent.llm_agent import LLMAgent
from league.llm.client import LLMClient
from league.logger.game_logger import GameLogger
from league.tools.base import Tool
from league.types import GameConfig, Player


def load_config(config_path: str = "config/default.yaml") -> dict:
    """Load configuration file"""
    path = Path(config_path)
    if not path.exists():
        print(f"Config not found: {config_path}, using defaults")
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def setup_logging(config: dict) -> None:
    """Configure logging"""
    log_config = config.get("logging", {})
    level_str = log_config.get("level", "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def create_llm_client(llm_config: dict) -> LLMClient:
    """Create an LLMClient from config dict"""
    return LLMClient(
        model=llm_config.get("model", "gpt-4o-mini"),
        base_url=llm_config.get("base_url"),
        api_key=llm_config.get("api_key"),
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 2048),
    )


def create_tools(config: dict) -> list[Tool]:
    """Create tool instances from config"""
    tools_config = config.get("tools", {})
    tools: list[Tool] = []

    img_config = tools_config.get("image_generation")
    if img_config:
        tools.append(
            ImageGenerationTool(
                model=img_config.get("model", "nano-banana"),
                base_url=img_config.get("base_url"),
                api_key=img_config.get("api_key"),
            )
        )

    return tools


async def run_draw_and_guess(config: dict) -> None:
    """Run the Draw and Guess game"""
    global_llm_config = config.get("llm", {})
    game_settings = config.get("game", {})
    player_configs = config.get("players", [])
    dg_config = config.get("draw_and_guess", {})

    # Create tools
    tools = create_tools(config)

    # Initialize Game Logger
    game_logger = GameLogger(game_name="draw_and_guess")

    # Create Players (each can have independent LLM config)
    players: list[Player] = []
    for i, pc in enumerate(player_configs):
        p_name = pc.get("name", f"Player_{i}")

        # Per-player LLM: merge global config with player-specific overrides
        player_llm_config = {**global_llm_config}
        if "llm" in pc and pc["llm"]:
            player_llm_config.update(pc["llm"])

        llm_client = create_llm_client(player_llm_config)
        agent = LLMAgent(name=p_name, llm_client=llm_client, tools=tools)
        players.append(
            Player(
                player_id=f"p{i}",
                name=p_name,
                agent=agent,
            )
        )

    # Initialize Engine
    engine = DrawAndGuessEngine(game_logger=game_logger)

    # Configure Game
    game_config = GameConfig(
        num_rounds=game_settings.get("num_rounds", len(players)),
        max_steps_per_round=game_settings.get("max_steps_per_round", 10),
        timeout_seconds=game_settings.get("timeout_seconds", 30.0),
        extra={"word_pool": dg_config.get("word_pool", [])},
    )

    print(f"\n{'=' * 20} Game Start: Draw and Guess {'=' * 20}")
    print(f"Players: {', '.join(p.name for p in players)}")
    print(f"Total Rounds: {game_config.num_rounds}\n")

    # Run Game
    result = await engine.run(players, game_config)

    # Export Logs
    log_dir = Path(config.get("logging", {}).get("output_dir", "logs"))
    log_file = log_dir / f"game_{int(asyncio.get_event_loop().time())}.json"
    game_logger.export(log_file)

    print(f"\n{'=' * 20} Game Over {'=' * 20}")
    print("Final Rankings:")
    for i, (pid, score) in enumerate(result.rankings):
        p_name = next(p.name for p in players if p.player_id == pid)
        print(f"{i + 1}. {p_name}: {score} points")
    print(f"\nDetailed logs saved to: {log_file}")


async def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/default.yaml"
    config = load_config(config_path)
    setup_logging(config)

    game_name = config.get("game", {}).get("name", "draw_and_guess")
    if game_name == "draw_and_guess":
        await run_draw_and_guess(config)
    else:
        print(f"Unsupported game type: {game_name}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGame terminated by user.")
