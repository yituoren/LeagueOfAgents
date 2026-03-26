"""长短期记忆管理"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    """记忆条目"""
    content: str
    round_num: int = 0
    step_num: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class Memory:
    """Agent记忆管理器

    支持：
    - 短期记忆：当前轮的交互历史（deque限长）
    - 长期记忆：跨轮的关键信息
    """

    def __init__(self, short_term_capacity: int = 50) -> None:
        self.short_term: deque[MemoryEntry] = deque(
            maxlen=short_term_capacity
        )
        self.long_term: list[MemoryEntry] = []

    def add(self, entry: MemoryEntry, long_term: bool = False) -> None:
        """添加记忆"""
        self.short_term.append(entry)
        if long_term:
            self.long_term.append(entry)

    def get_recent(self, n: int = 10) -> list[MemoryEntry]:
        """获取最近n条短期记忆"""
        items = list(self.short_term)
        return items[-n:]

    def retrieve(self, query: str, top_k: int = 5) -> list[MemoryEntry]:
        """检索相关长期记忆（基础实现：关键词匹配）"""
        scored: list[tuple[float, MemoryEntry]] = []
        keywords = set(query.lower().split())
        for entry in self.long_term:
            content_words = set(entry.content.lower().split())
            overlap = len(keywords & content_words)
            if overlap > 0:
                scored.append((overlap, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]

    def clear(self, long_term: bool = False) -> None:
        """清空记忆"""
        self.short_term.clear()
        if long_term:
            self.long_term.clear()
