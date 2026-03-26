# League of Agents API 参考文档

## 核心类型 (`league.types`)

### Observation
玩家观测信息，信息隔离的核心载体。

| 字段 | 类型 | 说明 |
|------|------|------|
| `round_num` | `int` | 当前轮次 |
| `step_num` | `int` | 当前步骤 |
| `player_role` | `str` | 玩家角色 |
| `visible_state` | `dict[str, Any]` | 可见游戏状态 |
| `action_prompt` | `str` | 动作提示文本 |
| `available_actions` | `list[str] \| None` | 可选动作列表 |
| `history` | `list[dict]` | 历史记录 |

### Action
玩家动作。

| 字段 | 类型 | 说明 |
|------|------|------|
| `action_type` | `str` | 动作类型 |
| `content` | `str` | 动作内容 |
| `metadata` | `dict[str, Any]` | 元数据 |

### PlayerAction
带玩家ID和时间戳的动作记录。

| 字段 | 类型 | 说明 |
|------|------|------|
| `player_id` | `str` | 玩家ID |
| `action` | `Action` | 动作 |
| `timestamp` | `float` | 时间戳 |

### Player
玩家实例。

| 字段 | 类型 | 说明 |
|------|------|------|
| `player_id` | `str` | 唯一标识 |
| `name` | `str` | 显示名 |
| `agent` | `Agent` | 智能体实例 |
| `role` | `str` | 当前角色 |
| `score` | `float` | 累计分数 |

### GameConfig
游戏配置。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `num_rounds` | `int` | `1` | 游戏轮数 |
| `max_steps_per_round` | `int` | `100` | 每轮最大步数 |
| `timeout_seconds` | `float` | `30.0` | 超时时间 |
| `extra` | `dict` | `{}` | 额外配置 |

### GameResult / RoundResult
游戏和轮次结果。

### JudgeContext / JudgeResult
裁判判定的输入和输出。

---

## GameEngine (`league.engine.base`)

游戏引擎抽象基类，实现 Game → Round → Step 三层模板方法。

### 主入口
```python
async def run(self, players: list[Player], config: GameConfig) -> GameResult
```

### Game层（需实现）
```python
async def on_game_start(self) -> None
def is_game_over(self) -> bool
def get_results(self) -> GameResult
```

### Round层（需实现）
```python
async def init_round(self, round_num: int) -> None
def is_round_over(self) -> bool
async def end_round(self, round_num: int) -> None
```

### Step层
模板方法 `execute_step()` 提供默认流程，子方法需实现：

```python
def get_active_players(self) -> list[str]          # 谁行动
def is_concurrent_step(self) -> bool                # 并发还是顺序（默认False）
def build_observation(self, player_id: str) -> Observation  # 构建观测
def validate_action(self, player_id: str, action: Action) -> Action  # 验证
async def apply_actions(self, actions: list[PlayerAction]) -> None   # 应用
def step_transition(self) -> None                   # 状态转换
```

可重写的默认实现：
```python
async def query_players_concurrent(self, player_ids) -> list[PlayerAction]
async def query_players_sequential(self, player_ids) -> list[PlayerAction]
```

---

## Agent (`league.agent.base`)

```python
class Agent(ABC):
    async def act(self, observation: Observation) -> Action  # 核心接口
    def reset(self) -> None                                  # 重置状态
```

### LLMAgent (`league.agent.llm_agent`)

基于LLM的Agent实现。

```python
LLMAgent(name, llm_client, system_prompt="", memory_capacity=50)
```

- 自动管理对话记忆
- 支持 `<output>` 标签解析
- 通过 `system_prompt` 定制行为

---

## Memory (`league.agent.memory`)

```python
memory = Memory(short_term_capacity=50)
memory.add(entry, long_term=False)      # 添加记忆
memory.get_recent(n=10)                  # 获取近期记忆
memory.retrieve(query, top_k=5)          # 检索长期记忆
memory.clear(long_term=False)            # 清空
```

---

## Referee (`league.referee.base`)

```python
class Referee(ABC):
    async def judge(self, context: JudgeContext) -> JudgeResult
```

### LLMReferee (`league.referee.llm_referee`)
基于LLM的语义判定裁判，适用于自然语言答案的模糊匹配。

---

## LLMClient (`league.llm.client`)

统一异步LLM客户端，基于OpenAI SDK。

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
