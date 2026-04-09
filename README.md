# 🏆 League of Agents

> **An LLM "Gladiator Arena"** — Evaluating and showcasing AI's reasoning, game theory, and memory capabilities through strategic games.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 📖 Overview

**League of Agents** is a multi-agent gaming framework. It encapsulates Large Language Models (LLMs) into independent agents and lets them compete in strategic games like *Draw and Guess*, *Werewolf*, and *Undercover*.

This provides an intuitive and entertaining way to evaluate models' logical reasoning, strategic play, long-term memory, and instruction-following abilities in complex, dynamic, and Partially Observable Markov Decision Process (POMDP) scenarios.

### Contents

- [Overview](#overview)
- [Who It's For](#who-its-for)
- [Core Architecture](#core-architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [License](#license)

### At a Glance

- Unified `Game -> Round -> Step` lifecycle for building turn-based multi-agent games.
- ReAct-style agents with tool calling, memory, and isolated observations.
- Async-first engine design for concurrent actions and provider API calls.
- Config-driven loading for engines, tools, and referees with minimal hardcoding.
- A concrete example game is included in `games/draw_and_guess/`.

### Who It's For

- **General Public & Enthusiasts**: Move beyond dry, static benchmarks. Experience the intelligence differences between various LLMs through live, entertaining game matches.
- **AI Researchers & Developers**: Utilize a dynamic POMDP interaction sandbox for zero-shot capability testing and reinforcement learning (RL) post-training.

---

## 🏗️ Core Architecture

### Three-Layer Game Model: `Game` → `Round` → `Step`

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

### Agent Architecture

Each agent follows a **ReAct** (Reason → Act → Observe) loop within a single turn:

```text
act(observation)
  └→ while True:
       ├→ LLM outputs <thought> (private reasoning)
       ├→ LLM calls tool? → execute tool → observe result → loop back
       └→ LLM outputs <output> (final action) → return
```

Agents structure their responses using XML tags:

| Tag | Required | Description |
| :--- | :--- | :--- |
| `<thought>` | Every response | Private reasoning, never revealed to other players |
| `<memory>` | Optional | Self-selected notes saved for future turns (agent-controlled memory) |
| `<output>` | Final response only | The action submitted to the game engine |

The engine **only reads `<output>`** — all intermediate tool calls, reasoning, and metadata stay within the agent's ReAct loop. This means agents have full autonomy: a drawer can generate multiple images, evaluate them, and choose the best one, with the engine only seeing the final selection in `<output>`.

### Framework Features

| Feature | Description |
| :--- | :--- |
| **Engine-Driven** | **Push Mode**: The Engine controls the flow, distributes observations, and collects actions. Agents simply implement a single `act()` interface. |
| **Information Isolation** | Each Agent only sees the `Observation` explicitly built for it, strictly mimicking a human's partial perspective. |
| **Fully Asynchronous** | All Engine and Agent methods are `async`, natively supporting concurrent queries, API calls, and real-time interaction. |
| **Agent-Controlled Memory** | Agents decide what to remember via `<memory>` tags — no hardcoded injection. |
| **Tool Calling (ReAct)** | Agents can call tools (e.g., image generation) in a multi-step loop within a single turn. |
| **Output-Driven** | The engine only parses `<output>` from agents, making the interface universal regardless of tool usage. |
| **Dynamic Instantiation** | All components (engine, tools, referee) are loaded from config via `target` strings — no hardcoded imports. |
| **Extensible Templates** | `run()` and `execute_step()` provide default flow skeletons; subclassing a new game only requires overriding the necessary parts. |

> **Note:** The core agent LLM interaction uses the OpenAI SDK (compatible with most providers). Tools within games (e.g., using the official Gemini SDK for image generation) can use any SDK independently.

---

## 📂 Project Structure

```text
LeagueOfAgents/
├── league/                    # Core Framework
│   ├── engine/base.py         # GameEngine abstract base class
│   ├── agent/
│   │   ├── base.py            # Agent abstract base class
│   │   ├── llm_agent.py       # LLM-driven Agent (ReAct + tool calling + memory)
│   │   └── memory.py          # Short and long-term memory management
│   ├── referee/
│   │   ├── base.py            # Referee abstract base class
│   │   └── llm_referee.py     # LLM-based semantic referee
│   ├── prompts/               # General prompt templates
│   │   ├── agent.py           # Base prompt defining XML tags and ReAct rules
│   │   └── referee.py         # Base prompt for referees
│   ├── tools/
│   │   └── base.py            # Tool abstract base class
│   ├── llm/client.py          # Unified async LLM client (OpenAI SDK compatible)
│   ├── logger/game_logger.py  # Structured game logs (JSON export)
│   └── types.py               # Common type definitions
├── games/                     # Game Implementations
│   └── draw_and_guess/        # "Draw and Guess"
│       ├── engine.py          # Game-specific engine (drawing → guessing → settlement)
│       ├── referee.py         # Semantic scoring referee + target word selection
│       ├── tools.py           # ImageGenerationTool (Gemini Imagen API)
│       └── prompts.py         # Game-specific prompt templates
├── config/default.yaml        # Default configuration
├── doc/                       # Documentation
│   ├── architecture.md        # Architecture details
│   └── api_reference.md       # API reference
├── launch.sh                  # Launch script
└── main.py                    # CLI entry point
```

---

## 🚀 Quick Start

The quickest path is: install dependencies, add API keys, adjust `config/default.yaml`, then launch the game.

### 1. Environment Setup

```bash
conda create -n league python=3.11 -y
conda activate league
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the project root:

```bash
# Default key for all players
LLM_API_KEY=your-api-key

# Per-player keys (optional, name uppercased, spaces → underscores)
# PLAYER_ALICE_API_KEY=sk-alice-key
# PLAYER_BOB_API_KEY=sk-bob-key

# Image generation key (optional, falls back to LLM_API_KEY)
# IMAGE_GEN_API_KEY=your-image-gen-key
```

Key resolution order: `PLAYER_{NAME}_API_KEY` → `LLM_API_KEY` → `OPENAI_API_KEY`

### 3. Configure Game

Edit `config/default.yaml`. The config has three top-level sections: `llm`, `game`, and `logging`.

```yaml
# Global LLM config (default for all players and referee)
llm:
  model: "gemini-3.1-flash-lite-preview"
  base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"
  temperature: 0.7
  max_tokens: 2048

# Game definition — engine, players, tools, referee all nested here
game:
  target: "games.draw_and_guess"        # module path → auto-resolves GameEngine
  num_rounds: 6
  max_steps_per_round: 10
  timeout_seconds: 60.0

  players:
    - name: "Alice"
    - name: "Bob"
      llm:                              # Per-player LLM override
        model: "gpt-4o-mini"
        base_url: null                  # Uses default OpenAI endpoint
    - name: "Charlie"

  tools:
    - target: "games.draw_and_guess.tools:ImageGenerationTool"
      params:
        model: "imagen-4.0-fast-generate-001"
        base_url: "https://generativelanguage.googleapis.com/"

  referee:
    target: "games.draw_and_guess.referee:DrawAndGuessReferee"
    llm:
      temperature: 0.2

logging:
  level: "INFO"
  output_dir: "logs"
```

### 4. Run

```bash
bash launch.sh                      # Default config
bash launch.sh config/custom.yaml   # Custom config
```

Generated logs and other runtime artifacts will be written to the configured output directories.

---

## 📚 Documentation

- [Architecture Guide](doc/architecture.md): Deep dive into system design and module interactions.
- [API Reference](doc/api_reference.md): Complete interface definitions for framework extension.

## 📄 License

This project is licensed under the [MIT License](LICENSE).
