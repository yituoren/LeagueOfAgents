# League of Agents API Reference

## Core Types (`league.types`)

### Observation
Player observation information, the core carrier of information isolation.

| Field | Type | Description |
|------|------|------|
| `round_num` | `int` | Current round number |
| `step_num` | `int` | Current step number |
| `player_role` | `str` | Player role |
| `visible_state` | `dict[str, Any]` | Visible game state |
| `action_prompt` | `str` | Action prompt text |
| `available_actions` | `list[str] \| None` | List of available actions |
| `history` | `list[dict]` | History logs |

### Action
Player action.

| Field | Type | Description |
|------|------|------|
| `action_type` | `str` | Type of action |
| `content` | `str` | Content of the action |
| `metadata` | `dict[str, Any]` | Metadata |

### PlayerAction
Action record with player ID and timestamp.

| Field | Type | Description |
|------|------|------|
| `player_id` | `str` | Player ID |
| `action` | `Action` | Action object |
| `timestamp` | `float` | Timestamp |

### Player
Player instance.

| Field | Type | Description |
|------|------|------|
| `player_id` | `str` | Unique identifier |
| `name` | `str` | Display name |
| `agent` | `Agent` | Agent instance |
| `role` | `str` | Current role |
| `score` | `float` | Cumulative score |

### GameConfig
Game configuration.

| Field | Type | Default | Description |
|------|------|--------|------|
| `num_rounds` | `int` | `1` | Number of rounds |
| `max_steps_per_round` | `int` | `100` | Max steps per round |
| `timeout_seconds` | `float` | `30.0` | Timeout in seconds |
| `extra` | `dict` | `{}` | Extra configuration |

### GameResult / RoundResult
Results for the game and individual rounds.

### JudgeContext / JudgeResult
Input and output for referee judgment.

---

## GameEngine (`league.engine.base`)

Abstract base class for the game engine, implementing the Game → Round → Step three-layer template method.

### Main Entry
```python
async def run(self, players: list[Player], config: GameConfig) -> GameResult
```

### Game Layer (Required Implementation)
```python
async def on_game_start(self) -> None
def is_game_over(self) -> bool
def get_results(self) -> GameResult
```

### Round Layer (Required Implementation)
```python
async def init_round(self, round_num: int) -> None
def is_round_over(self) -> bool
async def end_round(self, round_num: int) -> None
```

### Step Layer
The template method `execute_step()` provides the default flow; sub-methods to implement:

```python
def get_active_players(self) -> list[str]          # Who acts
def is_concurrent_step(self) -> bool                # Concurrent or sequential (default False)
def build_observation(self, player_id: str) -> Observation  # Build observation
def validate_action(self, player_id: str, action: Action) -> Action  # Validate
async def apply_actions(self, actions: list[PlayerAction]) -> None   # Apply
def step_transition(self) -> None                   # State transition
```

Overridable default implementations:
```python
async def query_players_concurrent(self, player_ids) -> list[PlayerAction]
async def query_players_sequential(self, player_ids) -> list[PlayerAction]
```

---

## Agent (`league.agent.base`)

```python
class Agent(ABC):
    async def act(self, observation: Observation) -> Action  # Core interface
    def reset(self) -> None                                  # Reset state
```

### LLMAgent (`league.agent.llm_agent`)

LLM-based Agent implementation.

```python
LLMAgent(name, llm_client, system_prompt="", memory_capacity=50)
```

- Automatically manages conversation memory
- Supports `<output>` tag parsing
- Customizes behavior via `system_prompt`

---

## Memory (`league.agent.memory`)

```python
memory = Memory(short_term_capacity=50)
memory.add(entry, long_term=False)      # Add memory
memory.get_recent(n=10)                  # Get recent memory
memory.retrieve(query, top_k=5)          # Retrieve long-term memory
memory.clear(long_term=False)            # Clear memory
```

---

## Referee (`league.referee.base`)

```python
class Referee(ABC):
    async def judge(self, context: JudgeContext) -> JudgeResult
```

### LLMReferee (`league.referee.llm_referee`)
LLM-based semantic judgment referee, suitable for fuzzy matching of natural language answers.

---

## LLMClient (`league.llm.client`)

Unified async LLM client, based on the OpenAI SDK.

```python
client = LLMClient(model="gpt-4o-mini", base_url=None, temperature=0.7, max_tokens=2048)
response: str = await client.chat(messages, system="")
result: dict = await client.chat_with_tools(messages, tools, system="")
```

---

## GameLogger (`league.logger.game_logger`)

```python
logger = GameLogger(game_name="")
logger.log_event(event_type, round_num=0, step_num=0, player_id="", data=None)
logger.log_action(action: PlayerAction, round_num=0, step_num=0)
json_str = logger.export(output_path=None)
logger.clear()
```
