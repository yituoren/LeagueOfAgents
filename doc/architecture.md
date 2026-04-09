# League of Agents Architecture Documentation

## Overview

League of Agents is a multi-agent gaming framework that allows Large Language Models (LLMs) to participate in various strategic games as independent agents. The platform is implemented in pure Python, uses the OpenAI SDK for LLM calls (compatible with most providers), and supports CLI interaction.

## Core Architecture

### Three-Layer Game Model: Game → Round → Step

All games share a unified three-layer structure:

```
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

```
execute_step()
  ├→ get_active_players()          # Determines who acts in this step
  ├→ is_concurrent_step()?
  │   ├─ True  → query_concurrent()   # asyncio.gather (e.g., simultaneous guessing)
  │   └─ False → query_sequential()   # Sequential turns (e.g., taking turns to speak)
  │         For each: build_observation() → agent.act() → validate_action()
  ├→ apply_actions()               # Batch update the game state
  └→ step_transition()             # Advance phase/counters
```

### Design Principles

1. **Engine-Driven, Agent Passive Response** (Push Mode)
   - The Engine controls the flow, distributes observations, and collects actions.
   - Agents only need to implement the `act(observation) → action` interface.

2. **Information Isolation**
   - Each Agent can only see the `Observation` explicitly built for it.
   - The Engine controls information visibility through `build_observation()`.

3. **Fully Asynchronous**
   - All engine and agent methods are `async`.
   - Supports concurrent queries (e.g., multiple guessers answering simultaneously) and sequential queries (e.g., taking turns to speak).

4. **Output-Driven Communication**
   - The engine only reads the `<output>` content from agents. All intermediate tool calls, reasoning, and metadata stay within the agent's ReAct loop.
   - This ensures a clean, universal interface: regardless of what tools an agent used or how many steps it took, the engine always parses the same `<output>` format.

### Agent Architecture

Each agent follows a **ReAct** (Reason → Act → Observe) loop within a single turn:

```
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

Key design: `<output>` signals "I'm done". During intermediate tool-calling steps, the agent does NOT include `<output>` — only `<thought>` + tool calls. The engine parses the final `<output>` as the agent's action.

### Tool System

Tools are defined as subclasses of `Tool` and registered via the config file. Each tool exposes:
- `name`, `description`, `parameters` (JSON Schema) — converted to OpenAI function-calling format via `to_openai_schema()`.
- `async execute(**kwargs) → ToolResult` — returns content (text fed back to the LLM) and metadata (for internal use).

Agents can call tools multiple times in a single turn. The final decision (e.g., which generated image to use) is always expressed in `<output>`, giving the agent full control over its action.

### Dynamic Instantiation

All game components (engine, tools, referee) are loaded dynamically from the config via `instantiate_from_config()`. The `target` field supports:
- Module path with default class: `"games.draw_and_guess"` → resolves `GameEngine` from the module
- Explicit class reference: `"games.draw_and_guess.tools:ImageGenerationTool"`
- File path: `"path/to/file.py:ClassName"`

`_filter_kwargs()` introspects the factory's signature and drops unsupported kwargs, making it safe to pass extra parameters.

### Configuration Structure

The config has three top-level keys:

```yaml
llm:       # Global LLM settings (model, base_url, api_key, temperature, max_tokens)
game:      # Game definition — engine target, players, tools, referee, game parameters
logging:   # Log level and output directory
```

Everything game-specific lives under `game`:
- `target`: module/class to instantiate as the game engine
- `players`: list of player configs, each with optional per-player `llm` overrides
- `tools`: list of tool configs, each with `target` and `params`
- `referee`: referee config with `target` and optional `llm` overrides

### API Key Resolution

Keys are resolved per-player in this order:
1. `PLAYER_{NAME}_API_KEY` environment variable (name uppercased, spaces → underscores)
2. `LLM_API_KEY` environment variable
3. `OPENAI_API_KEY` environment variable

This allows different players to use different providers/models with separate API keys.

## Module Structure

```
league/                    # Core Framework
├── engine/base.py         # GameEngine abstract base class
├── agent/
│   ├── base.py            # Agent abstract base class
│   ├── llm_agent.py       # LLM-driven Agent (ReAct + tool calling + memory)
│   └── memory.py          # Short and long-term memory management
├── referee/
│   ├── base.py            # Referee abstract base class
│   └── llm_referee.py     # LLM-based semantic referee
├── prompts/               # General prompt templates
│   ├── agent.py           # Base prompt defining XML tags and ReAct rules
│   └── referee.py         # Base prompt for referees
├── tools/
│   └── base.py            # Tool abstract base class (Tool, ToolResult)
├── llm/client.py          # Unified async LLM client (OpenAI SDK compatible)
├── logger/game_logger.py  # Structured game logs (JSON export)
└── types.py               # Common type definitions

games/                     # Concrete game implementations
└── draw_and_guess/        # Draw and Guess
    ├── engine.py          # DrawAndGuessEngine (3-phase: drawing → guessing → settlement)
    ├── referee.py         # Semantic scoring referee + target word selection
    ├── tools.py           # ImageGenerationTool (Gemini Imagen API)
    └── prompts.py         # Game-specific prompt templates
```

## Data Flow

```
main.py
  ├→ load_config()                    # Parse YAML
  ├→ build_tools()                    # Instantiate tools from game.tools
  ├→ build_players()                  # Create players with per-player LLM clients
  ├→ build_referee()                  # Instantiate referee with its own LLM client
  ├→ instantiate_from_config(game)    # Create game engine from game.target
  └→ engine.run(players, config)
       ├→ on_game_start()
       └→ [Loop] init_round()
            └→ [Loop] execute_step()
                 ├→ get_active_players()     # Who acts?
                 ├→ build_observation(pid)   # Build private observation
                 ├→ agent.act(obs)           # Agent ReAct loop (may call tools)
                 ├→ validate_action()        # Validate legality
                 ├→ apply_actions()          # Parse <output>, update state
                 └→ step_transition()        # Advance phase
```

## Extending the Framework

### Adding a New Game

1. Create a new directory under `games/` (e.g., `games/werewolf/`).
2. Subclass `GameEngine` and implement all abstract methods.
3. Write game-specific prompt templates (appended after the general `AGENT_BASE_PROMPT`).
4. Optionally define a referee (subclass `LLMReferee`) and custom tools (subclass `Tool`).
5. Add a config file pointing `game.target` to your new module.

### Adding a New Tool

1. Subclass `Tool` from `league.tools.base`.
2. Define `name`, `description`, `parameters` (JSON Schema), and implement `async execute()`.
3. Register it in the config under `game.tools` with the appropriate `target` and `params`.

Agents automatically discover tools via function calling schemas — no agent code changes needed.

## LLM Compatibility

`LLMClient` is based on the OpenAI SDK and is compatible with all OpenAI-compatible APIs:
- OpenAI (GPT series)
- Google AI Studio / Gemini (via `/v1beta/openai/` endpoint)
- DeepSeek, and other compatible interfaces

Simply configure `base_url` and `model` to switch providers. Tools within games (e.g., `ImageGenerationTool`) can use any SDK independently.
