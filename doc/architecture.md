# League of Agents 架构文档

## 概述

League of Agents 是一个多智能体游戏博弈平台，让大模型作为独立智能体参与各种策略游戏。平台采用纯Python实现，基于OpenAI SDK调用LLM，支持CLI交互。

## 核心架构

### 三层游戏模型：Game → Round → Step

```
Game（一局完整游戏）
├── Round 1（一轮：如某玩家当作画者）
│   ├── Step 1: 作画者描述 [sequential]
│   ├── Step 2: 猜词者竞猜 [concurrent]
│   └── Step 3: 裁判判定   [engine内部]
├── Round 2
│   └── ...
└── 最终结算
```

- **Game层**：管理多轮游戏的生命周期，判断游戏结束条件，汇总最终结果
- **Round层**：管理单轮流程，包括角色分配、初始化和结算
- **Step层**：最小交互单元，支持顺序和并发两种模式

### 设计原则

1. **Engine驱动，Agent被动响应**（Push模式）
   - Engine负责控制流程、分发观测、收集动作
   - Agent只需实现 `act(observation) → action` 接口

2. **信息隔离**
   - 每个Agent只能看到自己的 `Observation`
   - Engine通过 `build_observation()` 控制信息可见性

3. **全异步**
   - 所有引擎和Agent方法均为 `async`
   - 支持并发query（如多人同时猜词）和顺序query（如轮流发言）

## 模块结构

```
league/                # 核心框架
├── engine/base.py     # GameEngine 抽象基类
├── agent/
│   ├── base.py        # Agent 抽象基类
│   ├── llm_agent.py   # LLM驱动的Agent
│   └── memory.py      # 长短期记忆
├── referee/
│   ├── base.py        # Referee 抽象基类
│   └── llm_referee.py # LLM裁判
├── llm/client.py      # 统一LLM客户端
├── logger/            # 日志系统
└── types.py           # 公共类型

games/                 # 具体游戏实现
└── draw_and_guess/    # 你画我猜
```

## 数据流

```
Engine.run()
  ├→ on_game_start()          # 初始化
  └→ [循环] init_round()
       └→ [循环] execute_step()
            ├→ get_active_players()     # 谁行动？
            ├→ build_observation(pid)   # 构建观测
            ├→ agent.act(obs)           # Agent决策
            ├→ validate_action()        # 验证合法性
            ├→ apply_actions()          # 更新状态
            └→ step_transition()        # 推进阶段
```

## 扩展新游戏

实现新游戏只需：

1. 继承 `GameEngine`，实现所有抽象方法
2. 定义游戏特有的Agent（可选，可直接用 `LLMAgent`）
3. 定义裁判逻辑（如需要模糊判定则继承 `LLMReferee`）
4. 编写Prompt模板

## LLM兼容性

`LLMClient` 基于 OpenAI SDK，兼容所有 OpenAI-compatible API：
- OpenAI (GPT系列)
- DeepSeek
- 其他兼容接口

通过 `base_url` 配置即可切换。
