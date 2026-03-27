# 🏆 League of Agents

> **An LLM "Gladiator Arena"** — Evaluating and showcasing AI's reasoning, game theory, and memory capabilities through strategic games.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 📖 Project Introduction

**League of Agents** is a multi-agent gaming framework. It encapsulates Large Language Models (LLMs) into independent agents and lets them compete in strategic games like *Draw and Guess*, *Werewolf*, and *Undercover*. 

This provides an intuitive and entertaining way to evaluate models' logical reasoning, strategic play, long-term memory, and instruction-following abilities in complex, dynamic, and Partially Observable Markov Decision Process (POMDP) scenarios.

### 🎯 Target Audience

- 🎮 **General Public & Enthusiasts**: Move beyond dry, static benchmarks. Experience the intelligence differences between various LLMs through live, entertaining game matches.
- 🔬 **AI Researchers & Developers**: Utilize a dynamic POMDP interaction sandbox for zero-shot capability testing and reinforcement learning (RL) post-training.

---

## 🏗️ Core Architecture

### 🧩 Three-Layer Game Model: `Game` → `Round` → `Step`

All games within the framework share a unified, strictly managed three-layer structure:

```text
Game (Full game lifecycle, manages multiple rounds)
├── Round 0 (Single round complete process)
│   ├── Step 0 [Sequential/Concurrent] ── Player Actions
│   ├── Step 1 ...
│   └── Step N ── Round end condition met
├── Round 1 ...
└── Game end condition met → GameResult
```

- **Game Layer**: Controls the overall lifecycle, schedules Rounds in a loop until `is_game_over()` returns `True`, and aggregates the final `GameResult`.
- **Round Layer**: Manages the single-round flow (role assignment, state initialization, scoring), executing Steps in a loop until `is_round_over()`.
- **Step Layer**: The smallest unit of interaction. It orchestrates sub-processes via template methods:

```text
execute_step()
  ├→ get_active_players()          # Determines who acts in this step
  ├→ is_concurrent_step()?
  │   ├─ True  → query_concurrent()   # asyncio.gather (e.g., simultaneous guessing)
  │   └─ False → query_sequential()   # Sequential turns (e.g., taking turns to speak)
  │         For each: build_observation() → agent.act() → validate_action()
  ├→ apply_actions()               # Batch update the game state
  └→ step_transition()             # Advance phase/counters
```

### ✨ Framework Features

| Feature | Description |
| :--- | :--- |
| ⚙️ **Engine-Driven** | **Push Mode**: The Engine controls the flow, distributes observations, and collects actions. Agents simply implement a single `act()` interface. |
| 🛡️ **Information Isolation** | Each Agent only sees the `Observation` explicitly built for it, strictly mimicking a human's partial perspective. |
| ⚡ **Fully Asynchronous** | All Engine and Agent methods are `async`, natively supporting concurrent queries, API calls, and real-time interaction. |
| 🛠️ **Extensible Templates** | `run()` and `execute_step()` provide default flow skeletons; subclassing a new game only requires overriding the necessary parts. |

---

## 📂 Project Structure

```text
LeagueOfAgents/
├── league/                    # 🧠 Core Framework
│   ├── engine/base.py         # GameEngine abstract base class
│   ├── agent/                 
│   │   ├── base.py            # Agent abstract base class
│   │   ├── llm_agent.py       # LLM-driven Agent implementation
│   │   └── memory.py          # Short and long-term memory management
│   ├── referee/               
│   │   ├── base.py            # Referee abstract base class
│   │   └── llm_referee.py     # LLM-based semantic referee
│   ├── llm/client.py          # Unified async LLM client (OpenAI SDK compatible)
│   ├── logger/game_logger.py  # Structured game logs (JSON export)
│   └── types.py               # Common type definitions
├── games/                     # 🎲 Game Implementations
│   └── draw_and_guess/        # "Draw and Guess"
│       ├── engine.py          # Game-specific engine
│       ├── agents.py          # DrawerAgent / GuesserAgent
│       ├── referee.py         # Game scoring referee
│       └── prompts.py         # Specialized prompt templates
├── config/default.yaml        # ⚙️ Default configuration
├── doc/                       # 📚 Documentation
│   ├── architecture.md        # Architecture details
│   └── api_reference.md       # API reference
└── main.py                    # 🚀 CLI entry point
```

---

## 🚀 Quick Start

### 1. Environment Preparation

Ensure you have Python 3.11+ installed.

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Edit `config/default.yaml` to adjust parameters such as the LLM model, API base URL, number of players, and word pools.

### 3. Run the Game

Ensure your API Key is configured in your environment or passed to the LLM client, then run:

```bash
# Using default configuration
python main.py

# Using custom configuration
python main.py config/custom.yaml
```

---

## 📚 Documentation

- [Architecture Guide](doc/architecture.md): Deep dive into system design and module interactions.
- [API Reference](doc/api_reference.md): Complete interface definitions for framework extension.

## 📄 License

This project is licensed under the [MIT License](LICENSE).