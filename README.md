# League of Agents：多智能体游戏博弈平台

> 大模型"斗蛐蛐"——在策略游戏中评估和展现AI的推理、博弈与记忆能力。

## 项目简介

League of Agents 是一个多智能体游戏博弈平台。它将大模型封装为独立的智能体，让它们在你画我猜、狼人杀、谁是卧底等策略游戏中相互对抗，从而直观地评估模型在复杂动态场景下的逻辑推理、策略博弈、长程记忆和指令遵循能力。

**面向两类用户：**

- **大众科普与娱乐**：告别枯燥的静态跑分，通过游戏对局直观感受不同模型的智能水平差异
- **模型训练与评估**：提供动态POMDP交互沙盒，支持zero-shot能力测试和强化学习后训练

## 核心架构

### 三层游戏模型：Game → Round → Step

所有游戏共享统一的三层结构：

```
Game（完整游戏，管理多轮）
├── Round 0（单轮完整流程）
│   ├── Step 0 [sequential/concurrent] ── 玩家行动
│   ├── Step 1 ...
│   └── Step N ── 轮次结束条件满足
├── Round 1 ...
└── 游戏结束条件满足 → GameResult
```

- **Game层**：控制游戏生命周期，循环调度Round直到 `is_game_over()` 返回True，最终汇总 `GameResult`
- **Round层**：管理单轮流程（角色分配、状态初始化、结算计分），循环执行Step直到 `is_round_over()`
- **Step层**：最小交互单元，通过模板方法编排子流程：

```
execute_step()
  ├→ get_active_players()          # 本step谁需要行动
  ├→ is_concurrent_step()?
  │   ├─ True  → query_players_concurrent()   # asyncio.gather 并发，按时间戳排序（抢答）
  │   └─ False → query_players_sequential()   # 逐个query，后者可见前者动作（讨论）
  │         每个玩家：build_observation() → agent.act() → validate_action()
  ├→ apply_actions()               # 批量更新游戏状态
  └→ step_transition()             # 推进阶段/计数器
```

### 项目特点

| 特点 | 说明 |
|------|------|
| Engine驱动，Agent被动响应 | Push模式——Engine控制流程、分发观测、收集动作；Agent仅实现单一接口 |
| 严格信息隔离 | 每个Agent只能看到 `build_observation()` 为其构建的 `Observation`，如同真人的局部视角 |
| 全异步 | 所有Engine和Agent方法均为 `async`，原生支持并发query和实时交互 |
| 模板方法 + 子方法重写 | `run()` 和 `execute_step()` 提供默认流程骨架，子类只需重写关心的部分 |

## 项目结构

```
LeagueOfAgents/
├── league/                    # 核心框架
│   ├── engine/base.py         # GameEngine 抽象基类（Game→Round→Step）
│   ├── agent/
│   │   ├── base.py            # Agent 抽象基类
│   │   ├── llm_agent.py       # LLM驱动的Agent（含记忆管理）
│   │   └── memory.py          # 长短期记忆
│   ├── referee/
│   │   ├── base.py            # Referee 抽象基类
│   │   └── llm_referee.py     # LLM语义裁判
│   ├── llm/client.py          # 统一异步LLM客户端（OpenAI SDK）
│   ├── logger/game_logger.py  # 对局日志（JSON导出）
│   └── types.py               # 公共类型定义
├── games/
│   └── draw_and_guess/        # 你画我猜实现
│       ├── engine.py           # 游戏引擎
│       ├── agents.py           # DrawerAgent / GuesserAgent
│       ├── referee.py          # 博弈计分裁判
│       └── prompts.py          # Prompt模板
├── config/default.yaml        # 默认配置
├── doc/
│   ├── architecture.md        # 架构文档
│   └── api_reference.md       # API参考
├── main.py                    # CLI入口
├── pyproject.toml
└── requirements.txt
```

## 快速开始

### 1. 环境准备

```bash
conda create -n league python=3.11 -y
conda activate league
pip install -r requirements.txt
```

### 2. 配置

编辑 `config/default.yaml` 按需调整LLM模型、玩家数量、词库等参数。

### 3. 运行

在 `launch.sh` 中填入你的 API Key，然后：

```bash
bash launch.sh                      # 使用默认配置
bash launch.sh config/custom.yaml   # 使用自定义配置
```

## 自定义新游戏

实现一个新游戏只需三步：

1. **继承 `GameEngine`**：实现 `on_game_start`、`init_round`、`build_observation` 等抽象方法
2. **定义Agent**（可选）：继承 `LLMAgent` 或直接使用基础实现
3. **定义Referee**（可选）：需要模糊判定时继承 `LLMReferee`

```python
class MyGameEngine(GameEngine):
    async def on_game_start(self) -> None: ...
    def is_game_over(self) -> bool: ...
    async def init_round(self, round_num: int) -> None: ...
    def build_observation(self, player_id: str) -> Observation: ...
    # ... 实现其余抽象方法
```

详见 [架构文档](doc/architecture.md) 和 [API参考](doc/api_reference.md)。

## 文档

- [架构文档](doc/architecture.md)：系统设计与模块说明
- [API参考](doc/api_reference.md)：完整接口定义

## License

MIT
