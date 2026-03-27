"""Short and Long-term Memory Management"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MemoryEntry:
    """Memory Entry"""

    content: str
    round_num: int = 0
    step_num: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class Memory:
    """Agent Memory Manager

    Supports:
    - Short-term memory: Interaction history for the current round (length-limited deque)
    - Long-term memory: Key information persisting across rounds
    """

    def __init__(self, short_term_capacity: int = 50) -> None:
        self.short_term: deque[MemoryEntry] = deque(maxlen=short_term_capacity)
        self.long_term: list[MemoryEntry] = []

    def add(self, entry: MemoryEntry, long_term: bool = False) -> None:
        """Add a memory entry"""
        self.short_term.append(entry)
        if long_term:
            self.long_term.append(entry)

    def get_recent(self, n: int = 10) -> list[MemoryEntry]:
        """Retrieve the most recent n short-term memory entries"""
        items = list(self.short_term)
        return items[-n:]

    def retrieve(self, query: str, top_k: int = 5) -> list[MemoryEntry]:
        """Retrieve relevant long-term memories (Basic implementation: Keyword matching)"""
        scored: list[tuple[int, MemoryEntry]] = []
        keywords = set(query.lower().split())
        for entry in self.long_term:
            content_words = set(entry.content.lower().split())
            overlap = len(keywords & content_words)
            if overlap > 0:
                scored.append((overlap, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:top_k]]

    def clear(self, long_term: bool = False) -> None:
        """Clear memory"""
        self.short_term.clear()
        if long_term:
            self.long_term.clear()
