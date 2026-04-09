"""League of Agents - CLI Entry Point"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from league.agent.llm_agent import LLMAgent
from league.llm.client import LLMClient
from league.logger.game_logger import GameLogger
from league.tools.base import Tool
from league.types import GameConfig, Player

logger = logging.getLogger(__name__)


# ========== Config & Logging ==========


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


# ========== Dynamic Instantiation ==========


def _load_module_by_ref(module_ref: str) -> Any:
    """Load module from import path or file path."""
    if module_ref.endswith(".py") or "/" in module_ref or module_ref.startswith("."):
        module_path = Path(module_ref)
        if not module_path.is_absolute():
            module_path = (Path.cwd() / module_path).resolve()
        if not module_path.exists():
            raise FileNotFoundError(f"Target file not found: {module_path}")
        module_name = f"_loa_dynamic_{module_path.stem}_{abs(hash(str(module_path)))}"
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from file: {module_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return importlib.import_module(module_ref)


def _resolve_target(target: str, default_attr: str | None = None) -> Any:
    """Resolve target string into a callable/class.

    Formats: "module.path:ClassName", "module.path" (with default_attr),
             "path/to/file.py:ClassName"
    """
    if ":" in target:
        module_ref, attr_name = target.rsplit(":", 1)
        module = _load_module_by_ref(module_ref)
    elif default_attr is not None:
        try:
            spec = importlib.util.find_spec(target)
        except (ModuleNotFoundError, ValueError):
            spec = None
        if spec is not None:
            module = importlib.import_module(target)
            attr_name = default_attr
        elif "." in target:
            module_ref, attr_name = target.rsplit(".", 1)
            module = _load_module_by_ref(module_ref)
        else:
            raise ValueError(f"Cannot resolve target '{target}'")
    elif "." in target:
        module_ref, attr_name = target.rsplit(".", 1)
        module = _load_module_by_ref(module_ref)
    else:
        raise ValueError(
            f"Invalid target '{target}'. Use 'module.path:ClassName' or 'module.path'."
        )

    obj = getattr(module, attr_name)
    if not callable(obj):
        raise TypeError(f"Target '{target}' resolved to non-callable '{attr_name}'")
    return obj


def _filter_kwargs(factory: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Keep only kwargs accepted by the factory's signature."""
    callable_obj = factory.__init__ if inspect.isclass(factory) else factory
    sig = inspect.signature(callable_obj)
    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return kwargs
    accepted = {
        name
        for name, p in sig.parameters.items()
        if name != "self"
        and p.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    return {k: v for k, v in kwargs.items() if k in accepted}


def instantiate_from_config(
    section_config: dict[str, Any],
    default_kwargs: dict[str, Any] | None = None,
    default_attr: str | None = None,
) -> Any:
    """Instantiate an object from a config section with `target` and optional `params`."""
    target = section_config.get("target")
    if not target:
        raise ValueError(f"Missing `target` in config section: {section_config}")

    params = section_config.get("params", {}) or {}
    kwargs: dict[str, Any] = {}
    if default_kwargs:
        kwargs.update(default_kwargs)
    kwargs.update(params)

    factory = _resolve_target(str(target), default_attr=default_attr)
    return factory(**_filter_kwargs(factory, kwargs))


# ========== LLM & API Key ==========


def resolve_api_key(player_name: str | None = None) -> str | None:
    """PLAYER_{NAME}_API_KEY > LLM_API_KEY > OPENAI_API_KEY"""
    if player_name:
        env_name = f"PLAYER_{player_name.upper().replace(' ', '_')}_API_KEY"
        player_key = os.getenv(env_name)
        if player_key:
            return player_key
    return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")


def create_llm_client(
    llm_config: dict, player_name: str | None = None
) -> LLMClient:
    """Create LLMClient. Key resolution: config > per-player env > global env."""
    api_key = llm_config.get("api_key") or resolve_api_key(player_name)
    return LLMClient(
        model=llm_config.get("model", "gpt-4o-mini"),
        base_url=llm_config.get("base_url"),
        api_key=api_key,
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 2048),
    )


# ========== Build Game Components ==========


def build_tools(
    tools_config: list[dict[str, Any]],
) -> list[Tool]:
    """Recursively instantiate tools from game.tools config."""
    tools: list[Tool] = []
    for tc in tools_config:
        # Inject api_key from env if not in params
        params = dict(tc.get("params", {}) or {})
        if not params.get("api_key"):
            params["api_key"] = (
                os.getenv("IMAGE_GEN_API_KEY")
                or os.getenv("LLM_API_KEY")
                or os.getenv("OPENAI_API_KEY")
            )
        tool = instantiate_from_config(tc, default_kwargs=params)
        tools.append(tool)
        logger.info(f"Tool loaded: {tool.name}")
    return tools


def build_players(
    player_configs: list[dict[str, Any]],
    global_llm_config: dict,
    tools: list[Tool],
) -> list[Player]:
    """Create Player objects with per-player LLM clients."""
    players: list[Player] = []
    for i, pc in enumerate(player_configs):
        p_name = pc.get("name", f"Player_{i}")

        # Merge global LLM config with player-specific overrides
        player_llm_config = {**global_llm_config}
        if pc.get("llm"):
            player_llm_config.update(pc["llm"])

        llm_client = create_llm_client(player_llm_config, player_name=p_name)
        agent = LLMAgent(name=p_name, llm_client=llm_client, tools=tools)
        players.append(
            Player(player_id=f"p{i}", name=p_name, agent=agent)
        )
    return players


def build_referee(
    referee_config: dict[str, Any] | None,
    global_llm_config: dict,
) -> Any | None:
    """Recursively instantiate referee from game.referee config."""
    if not referee_config or not referee_config.get("target"):
        return None

    # Referee gets its own LLM client (with optional overrides)
    referee_llm_config = {**global_llm_config}
    if referee_config.get("llm"):
        referee_llm_config.update(referee_config["llm"])

    referee_client = create_llm_client(referee_llm_config)
    return instantiate_from_config(
        referee_config,
        default_kwargs={"llm_client": referee_client},
        default_attr="Referee",
    )


# ========== Main ==========


async def run_game(config: dict) -> None:
    """Build and run a game entirely from config."""
    global_llm_config = config.get("llm", {})
    game_config = config.get("game", {})

    # Recursively build all sub-components from game config
    tools = build_tools(game_config.get("tools", []))
    players = build_players(game_config.get("players", []), global_llm_config, tools)
    referee = build_referee(game_config.get("referee"), global_llm_config)

    # Instantiate engine from game.target
    game_name = game_config.get("name", "game")
    game_logger = GameLogger(game_name=game_name)
    engine = instantiate_from_config(
        game_config,
        default_kwargs={"game_logger": game_logger},
        default_attr="GameEngine",
    )
    engine.referee = referee

    # Build GameConfig
    gc = GameConfig(
        num_rounds=game_config.get("num_rounds", len(players)),
        max_steps_per_round=game_config.get("max_steps_per_round", 10),
        timeout_seconds=game_config.get("timeout_seconds", 30.0),
    )

    print(f"\n{'=' * 20} Game Start: {game_name} {'=' * 20}")
    print(f"Players: {', '.join(p.name for p in players)}")
    print(f"Total Rounds: {gc.num_rounds}\n")

    result = await engine.run(players, gc)

    # Export logs
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
    load_dotenv()
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/default.yaml"
    config = load_config(config_path)
    setup_logging(config)
    await run_game(config)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGame terminated by user.")
