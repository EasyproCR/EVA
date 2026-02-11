from __future__ import annotations
from dataclasses import dataclass, field
from time import time
from typing import Any, Dict, List, Optional

@dataclass
class ConversationState:
    last_listings: List[Dict[str, Any]] = field(default_factory=list)
    last_selected_id: Optional[int] = None
    updated_at: float = field(default_factory=time)

class SessionStore:
    def __init__(self, ttl_seconds: int = 60 * 30):  # 30 min
        self._ttl = ttl_seconds
        self._store: Dict[str, ConversationState] = {}

    def get(self, session_id: str) -> ConversationState:
        self._gc()
        state = self._store.get(session_id)
        if state is None:
            state = ConversationState()
            self._store[session_id] = state
        return state

    def set_selected(self, session_id: str, listing_id: Optional[int]) -> None:
        state = self.get(session_id)
        state.last_selected_id = listing_id
        state.updated_at = time()

    def set_listings(self, session_id: str, listings: List[Dict[str, Any]]) -> None:
        state = self.get(session_id)
        state.last_listings = listings
        state.last_selected_id = listings[0]["id"] if len(listings) == 1 else None
        state.updated_at = time()

    def clear(self, session_id: str) -> None:
        self._store.pop(session_id, None)

    def _gc(self) -> None:
        now = time()
        dead = [k for k, v in self._store.items() if (now - v.updated_at) > self._ttl]
        for k in dead:
            self._store.pop(k, None)
