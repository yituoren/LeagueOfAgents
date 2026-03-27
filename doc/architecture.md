# League of Agents Architecture Documentation

## Overview

League of Agents is a multi-agent gaming framework that allows Large Language Models (LLMs) to participate in various strategic games as independent agents. The platform is implemented in pure Python, based on the OpenAI SDK for LLM calls, and supports CLI interaction.

## Core Architecture

### Three-Layer Game Model: Game → Round → Step

```
Game (A complete match)
├── Round 1 (One round: e.g., a specific player acts as the drawer)
│   ├── Step 1: Drawer's description [sequential]
│   ├── Step 2: Guessers' guesses     [concurrent]
│   └── Step 3: Referee's judgment    [internal engine logic]
├── Round 2
│   └── ...
└── Final Settlement
```

- **Game Layer**: Manages the lifecycle of multiple rounds, determines game-over conditions, and aggregates final results.
- **Round Layer**: Manages the flow of a single round, including role assignment, initialization, and settlement.
- **Step Layer**: The smallest unit of interaction, supporting both sequential and concurrent execution modes.

### Design Principles

1. **Engine-Driven, Agent Passive Response** (Push Mode)
   - The Engine is responsible for controlling the flow, distributing observations, and collecting actions.
   - Agents only need to implement the `act(observation) → action` interface.

2. **Information Isolation**
   - Each Agent can only see its own `Observation`.
   - The Engine controls information visibility through the `build_observation()` method.

3. **Fully Asynchronous**
   - All engine and agent methods are `async`.
   - Supports concurrent queries (e.g., multiple people guessing simultaneously) and sequential queries (e.g., taking turns to speak).

## Module Structure

```
league/                # Core Framework
├── engine/base.py     # GameEngine abstract base class
├── agent/
│   ├── base.py        # Agent abstract base class
│   ├── llm_agent.py   # LLM-driven Agent
│   └── memory.py      # Short and long-term memory
├── referee/
│   ├── base.py        # Referee abstract base class
│   └── llm_referee.py # LLM Referee
├── llm/client.py      # Unified LLM Client
├── logger/            # Logging system
└── types.py           # Common types

games/                 # Concrete game implementations
└── draw_and_guess/    # Draw and Guess implementation
```

## Data Flow

```
Engine.run()
  ├→ on_game_start()          # Initialization
  └→ [Loop] init_round()
       └→ [Loop] execute_step()
            ├→ get_active_players()     # Who acts?
            ├→ build_observation(pid)   # Build observation
            ├→ agent.act(obs)           # Agent decision
            ├→ validate_action()        # Validate legality
            ├→ apply_actions()          # Update state
            └→ step_transition()        # Advance phase
```

## Extending New Games

To implement a new game, you only need to:

1. Inherit from `GameEngine` and implement all abstract methods.
2. Define game-specific Agents (optional, you can use `LLMAgent` directly).
3. Define referee logic (if fuzzy matching is needed, inherit from `LLMReferee`).
4. Write Prompt templates.

## LLM Compatibility

`LLMClient` is based on the OpenAI SDK and is compatible with all OpenAI-compatible APIs:
- OpenAI (GPT series)
- DeepSeek
- Other compatible interfaces

Simply configure the `base_url` to switch providers.