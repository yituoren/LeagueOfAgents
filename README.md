# League of Agents: A Multi-Agent Gaming Framework

> LLM "Gladiator Arena" — evaluating and showcasing AI's reasoning, game theory, and memory capabilities through strategic games.

## Project Introduction

League of Agents is a multi-agent gaming framework. It encapsulates Large Language Models (LLMs) into independent agents and lets them compete in strategic games like Draw and Guess, Werewolf, and Undercover. This provides an intuitive way to evaluate models' logical reasoning, strategic play, long-term memory, and instruction-following abilities in complex, dynamic scenarios.

**Targeted at two types of users:**

- **General Public & Enthusiasts**: Move beyond dry static benchmarks and experience the intelligence differences between models through live game matches.
- **Model Training & Evaluation**: Provides a dynamic POMDP (Partially Observable Markov Decision Process) interaction sandbox, supporting zero-shot capability testing and reinforcement learning post-training.

## Core Architecture

### Three-Layer Game Model: Game → Round → Step

All games share a unified three-layer structure:

```
Game (Full game, manages multiple rounds)
├── Round 0 (Single round complete process)
│   ├── Step 0 [sequential/concurrent] ── Player actions
│   ├── Step 1 ...
│   └── Step N ── Round end condition met
├── Round 1 ...
└── Game end condition met → GameResult
```

- **Game Layer**: Controls the game lifecycle, schedules Rounds in a loop until `is_game_over()` returns True, and finally aggregates the `GameResult`.
- **Round Layer**: Manages the single-round flow (role assignment, state initialization, scoring), executing Steps in a loop until `is_round_over()`.
- **Step Layer**: The smallest unit of interaction, orchestrating sub-processes via template methods:

```
execute_step()
  ├→ get_active_players()          # Who needs to act in this step
  ├→ is_concurrent_step()?
  │   ├─ True  → query_players_concurrent()   # asyncio.gather concurrent, sorted by timestamp
  │   └─ False → query_players_sequential()   # Sequential queries, later players see earlier actions
  │         Each player: build_observation() → agent.act() → validate_action()
  ├→ apply_actions()               # Batch update game state
  └→ step_transition()             # Advance phase/counters
```

### Project Features

| Feature | Description |
|------|------|
| Engine-Driven, Agent Passive | Push Mode — Engine controls flow, distributes observations, and collects actions; Agent only implements a single interface. |
| Strict Information Isolation | Each Agent only sees the `Observation` built for it by `build_observation()`, mimicking a human's partial perspective. |
| Fully Asynchronous | All Engine and Agent methods are `async`, natively supporting concurrent queries and real-time interaction. |
| Template Method + Sub-method Overriding | `run()` and `execute_step()` provide default flow skeletons; subclasses only need to override parts they care about. |

## Project Structure

```
LeagueOfAgents/
├── league/                    # Core Framework
│   ├── engine/base.py         # GameEngine abstract base class (Game→Round→Step)
│   ├── agent/
│   │   ├── base.py            # Agent abstract base class
│   │   ├── llm_agent.py       # LLM-driven Agent (with memory management)
│   │   └── memory.py          # Short and long-term memory
│   ├── referee/
│   │   ├── base.py            # Referee abstract base class
│   │   └── llm_referee.py     # LLM semantic referee
│   ├── llm/client.py          # Unified async LLM client (OpenAI SDK)
│   ├── logger/game_logger.py  # Game logs (JSON export)
│   └── types.py               # Common type definitions
├── games/
│   └── draw_and_guess/        # Draw and Guess implementation
│       ├── engine.py           # Game engine
│       ├── agents.py           # DrawerAgent / GuesserAgent
│       ├── referee.py          # Game scoring referee
│       └── prompts.py          # Prompt templates
├── config/default.yaml        # Default configuration
├── doc/
│   ├── architecture.md        # Architecture documentation
│   └── api_reference.md       # API reference
├── main.py                    # CLI entry point
├── pyproject.toml
└── requirements.txt
```

## Quick Start

### 1. Environment Preparation

```bash
pip install -r requirements.txt
```

### 2. Configuration

Edit `config/default.yaml` to adjust parameters like LLM models, number of players, and word pools as needed.

### 3. Run

Fill in your API Key in `launch.sh`, then:

```bash
bash launch.sh                      # Use default config
bash launch.sh config/custom.yaml   # Use custom config
```
