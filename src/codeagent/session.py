"""
Session management service for AlpieCode.

Manages conversation state containers (Session) and session lifecycle (SessionManager).
"""

import uuid
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from .context import ContextManager
from .executor import ToolExecutor


@dataclass
class Session:
    """Conversation session containing context and tool executor."""
    id: str
    workdir: Path
    context: ContextManager
    executor: ToolExecutor
    created_at: float = field(default_factory=time.time)
    is_offline: bool = False
    cancelled: bool = False


class SessionManager:
    """Manages creation, retrieval, and destruction of active sessions."""

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create_session(
        self,
        workdir: Path,
        max_tokens: int = 262_144,
        session_id: Optional[str] = None,
    ) -> Session:
        sid = session_id or str(uuid.uuid4())[:8]
        session = Session(
            id=sid,
            workdir=workdir.resolve(),
            context=ContextManager(max_tokens=max_tokens),
            executor=ToolExecutor(workdir.resolve()),
        )
        self._sessions[sid] = session
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def list_sessions(self) -> List[dict]:
        return [
            {
                "id": s.id,
                "workdir": str(s.workdir),
                "created_at": s.created_at,
                "estimated_tokens": s.context.estimate_tokens(),
            }
            for s in self._sessions.values()
        ]

    def cleanup_expired(self, max_age_seconds: float = 3600) -> int:
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if (now - s.created_at) > max_age_seconds]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)
