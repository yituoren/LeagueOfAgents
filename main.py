"""League of Agents - CLI入口"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import yaml

from league.llm.client import LLMClient
from league.types import GameConfig, Player
from games.draw_and_guess.agents import DrawerAgent, GuesserAgent
from games.draw_and_guess.engine import DrawAndGuessEngine
from games.draw_and_guess.referee import DrawAndGuessReferee


def load_config(config_path: str = "config/default.yaml") -> dict:
    """加载配置文件"""
    path = Path(config_path)
    if not path.exists():
        print(f"Config not found: {config_path}, using defaults")
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def setup_logging(config: dict) -> None:
    """配置日志"""
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )


async def run_draw_and_guess(config: dict) -> None:
    """运行你画我猜游戏"""
    llm_config = config.get("llm", {})
    game_config = config.get("game", {})
    player_configs = config.get("players", [{"name": f"Player{i}"} for i in range(4)])

    # 创建LLM客户端
    llm_client = LLMClient(
        model=llm_config.get("model", "gpt-4o-mini"),
        base_url=llm_config.get("base_url"),
        temperature=llm_config.get("temperature", 0.7),
        max_tokens=llm_config.get("max_tokens", 2048),
    )

    # 创建玩家（每个玩家同时拥有drawer和guesser能力，由engine分配角色）
    players: list[Player] = []
    for i, pc in enumerate(player_configs):
        name = pc.get("name", f"Player{i}")
        pid = f"player_{i}"
        # 使用GuesserAgent作为默认agent，engine会根据角色发送不同observation
        agent = GuesserAgent(name=name, llm_client=llm_client)
        players.append(Player(player_id=pid, name=name, agent=agent))

    # 创建裁判和引擎
    referee = DrawAndGuessReferee(llm_client=llm_client)
    engine = DrawAndGuessEngine(referee=referee)

    # 配置自定义词库
    dag_config = config.get("draw_and_guess", {})
    if "word_pool" in dag_config:
        engine.word_pool = dag_config["word_pool"]

    # 运行游戏
    num_rounds = game_config.get("num_rounds", len(players))
    result = await engine.run(
        players=players,
        config=GameConfig(
            num_rounds=num_rounds,
            max_steps_per_round=game_config.get("max_steps_per_round", 10),
            timeout_seconds=game_config.get("timeout_seconds", 30.0),
        ),
    )

    # 输出结果
    print("\n" + "=" * 50)
    print("游戏结束！最终得分：")
    print("=" * 50)
    for pid, score in sorted(
        result.final_scores.items(), key=lambda x: x[1], reverse=True
    ):
        name = next(
            (p.name for p in players if p.player_id == pid), pid
        )
        print(f"  {name}: {score:.1f} 分")
    if result.winner:
        winner_name = next(
            (p.name for p in players if p.player_id == result.winner),
            result.winner,
        )
        print(f"\n冠军: {winner_name}!")
    print("=" * 50)

    # 导出日志
    log_dir = config.get("logging", {}).get("output_dir", "logs")
    Path(log_dir).mkdir(exist_ok=True)
    log_path = Path(log_dir) / "latest_game.json"
    engine.game_logger.export(log_path)
    print(f"\n对局日志已保存至: {log_path}")


def main() -> None:
    """CLI主入口"""
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/default.yaml"
    config = load_config(config_path)
    setup_logging(config)

    print("=" * 50)
    print("  League of Agents - 多智能体游戏博弈平台")
    print("=" * 50)
    print("\n启动游戏: 你画我猜\n")

    asyncio.run(run_draw_and_guess(config))


if __name__ == "__main__":
    main()
