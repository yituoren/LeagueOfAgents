# League of Agents API Reference

## Core Types (`league.types`)

### Observation
Player observation — the core carrier of information isolation.

| Field | Type | Description |
|-------|------|-------------|
| `round_num` | `int` | Current round number |
| `step_num` | `int` | Current step number |
| `player_role` | `str` | Player role (e.g., "drawer", "guesser") |
| `visible_state` | `dict[str, Any]` | Visible game state |
| `action_prompt` | `str` | Action prompt text |
| `available_actions` | `list[str] \| None` | List of available actions (optional) |
| `history` | `list[dict]` | History logs |

### Action
Player action, parsed from the agent's `<output>` tag.

| Field | Type | Description |
|-------|------|-------------|
| `action_type` | `str` | Type of action (e.g., "speak", "timeout") |
| `content` | `str` | Content of the action (from `<output>`) |
| `metadata` | `dict[str, Any]` | Metadata (e.g., raw LLM response) |

### PlayerAction
Action record with player ID and timestamp.

| Field | Type | Description |
|-------|------|-------------|
| `player_id` | `str` | Player ID |
| `action` | `Action` | Action object |
| `timestamp` | `float` | Timestamp (default: `time.time()`) |

### Player
Player instance.

| Field | Type | Description |
|-------|------|-------------|
| `player_id` | `str` | Unique identifier |
| `name` | `str` | Display name |
| `agent` | `Agent` | Agent instance |
| `role` | `str` | Current role (set per round) |
| `score` | `float` | Cumulative score |
| `metadata` | `dict[str, Any]` | Extra metadata |

### GameConfig
Game configuration.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `num_rounds` | `int` | `1` | Number of rounds |
| `max_steps_per_round` | `int` | `100` | Max steps per round |
| `timeout_seconds` | `float` | `30.0` | Per-player timeout |
| `extra` | `dict` | `{}` | Extra configuration |

### GameResult
Final game result.

| Field | Type | Description |
|-------|------|-------------|
| `winner_ids` | `list[str]` | Winning player IDs |
| `rankings` | `list[tuple[str, float]]` | Sorted (player_id, score) pairs |
| `metadata` | `dict[str, Any]` | Extra metadata |

### RoundResult
Result of a single round.

| Field | Type | Description |
|-------|------|-------------|
| `round_num` | `int` | Round number |
| `scores` | `dict[str, float]` | Player scores for this round |
| `winner_id` | `str \| None` | Round winner |
| `details` | `dict[str, Any]` | Extra details |

### JudgeContext
Input for referee judgment.

| Field | Type | Description |
|-------|------|-------------|
| `round_num` | `int` | Round number |
| `target` | `str` | Target answer |
| `actions` | `list[PlayerAction]` | Player actions to judge |
| `extra` | `dict[str, Any]` | Extra context (e.g., drawer_id, description) |

### JudgeResult
Output of referee judgment.

| Field | Type | Description |
|-------|------|-------------|
| `correct_players` | `list[str]` | IDs of players who answered correctly |
| `scores` | `dict[str, float]` | Score assignments per player |
| `reasoning` | `str` | Referee's reasoning |

---

## GameEngine (`league.engine.base`)

Abstract base class implementing the Game → Round → Step three-layer template method.

### Constructor
```python
GameEngine(game_logger: GameLogger | None = None)
```

Instance attributes:
- `players: list[Player]` — set by `run()`
- `players_map: dict[str, Player]` — player_id → Player lookup
- `config: GameConfig` — set by `run()`
- `referee: LLMReferee | None` — set externally after construction
- `current_round: int`, `current_step: int` — tracked automatically

### Main Entry
```python
async def run(self, players: list[Player], config: GameConfig) -> GameResult
```

### Game Layer (Abstract)
```python
async def on_game_start(self) -> None
def is_game_over(self) -> bool
def get_results(self) -> GameResult
```

### Round Layer (Abstract)
```python
async def init_round(self, round_num: int) -> None
def is_round_over(self) -> bool
async def end_round(self, round_num: int) -> None
```

### Step Layer
Template method `execute_step()` provides the default flow. Sub-methods to implement:

```python
def get_active_players(self) -> list[str]                          # Who acts
def is_concurrent_step(self) -> bool                               # Concurrent or sequential (default False)
def build_observation(self, player_id: str) -> Observation         # Build private observation
def validate_action(self, player_id: str, action: Action) -> Action  # Validate
async def apply_actions(self, actions: list[PlayerAction]) -> None   # Apply & update state
def step_transition(self) -> None                                  # Phase transition
```

Overridable default implementations:
```python
async def query_players_concurrent(self, player_ids: list[str]) -> list[PlayerAction]
async def query_players_sequential(self, player_ids: list[str]) -> list[PlayerAction]
```

---

## Agent (`league.agent.base`)

```python
class Agent(ABC):
    name: str
    async def act(self, observation: Observation) -> Action   # Core interface
    def reset(self) -> None                                   # Reset state
```

### LLMAgent (`league.agent.llm_agent`)

LLM-based Agent with ReAct tool calling and agent-controlled memory.

```python
LLMAgent(
    name: str,
    llm_client: LLMClient,
    system_prompt: str = "",       # Game-specific prompt (appended to base)
    memory_capacity: int = 50,
    tools: list[Tool] | None = None,
)
```

Key behaviors:
- **ReAct loop**: When tools are available, runs a loop of `<thought>` → tool call → observe → ... → `<output>`.
- **Agent-controlled memory**: Parses `<memory>` tags from LLM output and stores them. Memories are injected as `[Your Saved Memories]` in subsequent turns.
- **Output parsing**: Extracts `<output>` content as the action. Falls back to stripping `<thought>`/`<memory>` tags if no `<output>` is found.
- **Multimodal support**: Converts local image paths in `visible_state["image_url"]` to base64 data URLs for multimodal LLM input.

---

## Tool (`league.tools.base`)

```python
class Tool(ABC):
    name: str
    description: str
    parameters: dict[str, Any]   # JSON Schema

    async def execute(self, **kwargs: Any) -> ToolResult
    def to_openai_schema(self) -> dict[str, Any]   # Convert to OpenAI function calling format
```

### ToolResult
```python
@dataclass
class ToolResult:
    content: str                       # Text returned to the LLM
    metadata: dict[str, Any] = {}      # Internal metadata (not sent to LLM)
```

---

## Memory (`league.agent.memory`)

```python
memory = Memory(short_term_capacity=50)
memory.add(entry: MemoryEntry, long_term: bool = False)
memory.get_recent(n: int = 10) -> list[MemoryEntry]
memory.retrieve(query: str, top_k: int = 5) -> list[MemoryEntry]
memory.clear(long_term: bool = False)
```

Memory is agent-controlled: the LLM decides what to save by outputting `<memory>` tags. No hardcoded memory injection.

---

## Referee (`league.referee.base`)

```python
class Referee(ABC):
    async def judge(self, context: JudgeContext) -> JudgeResult
```

### LLMReferee (`league.referee.llm_referee`)

LLM-based semantic judgment referee. Subclass and override for game-specific behavior.

```python
LLMReferee(llm_client: LLMClient)
```

Game-specific referees (e.g., `DrawAndGuessReferee`) may add methods like `choose_target()` for word selection.

---

## LLMClient (`league.llm.client`)

Unified async LLM client based on the OpenAI SDK.

```python
client = LLMClient(
    model: str = "gpt-4o-mini",
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 2048,
)

response: str = await client.chat(messages, system="")
result: dict = await client.chat_with_tools(messages, tools, system="")
```

`chat_with_tools` returns:
- `content`: text response (if any)
- `tool_calls`: list of tool call objects (if any)
- `raw_message`: the original message dict (preserves provider-specific fields like Gemini's `thought_signature`)

---

## GameLogger (`league.logger.game_logger`)

```python
logger = GameLogger(game_name: str = "")
logger.log_event(event_type, round_num=0, step_num=0, player_id="", data=None)
logger.log_action(action: PlayerAction, round_num=0, step_num=0)
json_str = logger.export(output_path: Path | None = None)
logger.clear()
```

---

## Dynamic Instantiation (`main.py`)

### instantiate_from_config
```python
instantiate_from_config(
    section_config: dict[str, Any],
    default_kwargs: dict[str, Any] | None = None,
    default_attr: str | None = None,
) -> Any
```

Resolves `target` string to a class/factory, merges `params` with `default_kwargs`, filters unsupported kwargs via signature introspection, and returns the instantiated object.

### Build Functions
```python
build_tools(tools_config: list[dict]) -> list[Tool]
build_players(player_configs: list[dict], global_llm_config: dict, tools: list[Tool]) -> list[Player]
build_referee(referee_config: dict | None, global_llm_config: dict) -> Any | None
create_llm_client(llm_config: dict, player_name: str | None = None) -> LLMClient
resolve_api_key(player_name: str | None = None) -> str | None
```
