"""LLM驱动的Agent实现"""

from __future__ import annotations

import re

from league.agent.base import Agent
from league.agent.memory import Memory, MemoryEntry
from league.llm.client import LLMClient
from league.types import Action, Observation


class LLMAgent(Agent):
    """基于LLM的智能体

    通过LLMClient调用大模型，支持记忆管理和思维链。
    """

    def __init__(
        self,
        name: str,
        llm_client: LLMClient,
        system_prompt: str = "",
        memory_capacity: int = 50,
    ) -> None:
        self.name = name
        self.llm_client = llm_client
        self.system_prompt = system_prompt
        self.memory = Memory(short_term_capacity=memory_capacity)

    async def act(self, observation: Observation) -> Action:
        """接收观测，调用LLM生成动作"""
        messages = self._build_messages(observation)
        response = await self.llm_client.chat(
            messages=messages,
            system=self.system_prompt,
        )

        content = response.strip()
        action = self._parse_response(content, observation)

        self.memory.add(MemoryEntry(
            content=f"[action] {action.content}",
            round_num=observation.round_num,
            step_num=observation.step_num,
        ))

        return action

    def reset(self) -> None:
        """重置agent状态"""
        self.memory.clear()

    def _build_messages(self, observation: Observation) -> list[dict[str, str]]:
        """构建LLM消息列表"""
        messages: list[dict[str, str]] = []

        # 注入近期记忆
        recent = self.memory.get_recent(10)
        if recent:
            memory_text = "\n".join(e.content for e in recent)
            messages.append({
                "role": "user",
                "content": f"[历史记忆]\n{memory_text}",
            })
            messages.append({
                "role": "assistant",
                "content": "好的，我已了解历史信息。",
            })

        # 当前观测
        obs_parts = [
            f"第 {observation.round_num + 1} 轮，第 {observation.step_num + 1} 步",
            f"你的角色: {observation.player_role}",
        ]
        if observation.visible_state:
            state_str = "\n".join(
                f"  {k}: {v}" for k, v in observation.visible_state.items()
            )
            obs_parts.append(f"当前状态:\n{state_str}")
        obs_parts.append(f"\n{observation.action_prompt}")

        if observation.available_actions:
            obs_parts.append(
                f"可选动作: {', '.join(observation.available_actions)}"
            )

        messages.append({"role": "user", "content": "\n".join(obs_parts)})
        return messages

    def _parse_response(self, content: str, observation: Observation) -> Action:
        """解析LLM响应为Action

        支持 <output>...</output> 标签提取。
        """
        output_match = re.search(
            r"<output>(.*?)</output>", content, re.DOTALL
        )
        action_content = output_match.group(1).strip() if output_match else content

        return Action(
            action_type=observation.player_role,
            content=action_content,
            metadata={"raw_response": content},
        )
