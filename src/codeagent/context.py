"""
Conversation context manager for AlpieCode.

Manages the list of messages in a conversation session, tracking estimated tokens
and performing compaction when context limits are approached.
"""

from typing import Any, Dict, List, Optional

from .backends.base import ChatResponse, ToolCall
from .compaction import compact_messages, estimate_tokens, needs_compaction


def _serialize_assistant_message(msg: ChatResponse) -> dict:
    """Serialize a ChatResponse into OpenAI chat message dict format."""
    result = {"role": "assistant"}
    result["content"] = msg.content if msg.content else None

    if msg.tool_calls:
        import json
        result["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else tc.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return result


class ContextManager:
    """Manages session messages and context window token budgeting."""

    def __init__(self, max_tokens: int = 262_144):
        self.max_tokens = max_tokens
        self._messages: List[dict] = []

    @property
    def messages(self) -> List[dict]:
        return self._messages

    @messages.setter
    def messages(self, msgs: List[dict]) -> None:
        self._messages = msgs

    def set_system_prompt(self, prompt: str) -> None:
        if self._messages and self._messages[0].get("role") == "system":
            self._messages[0]["content"] = prompt
        else:
            self._messages.insert(0, {"role": "system", "content": prompt})

    def add_user_message(self, content: Any) -> None:
        self._messages.append({"role": "user", "content": content})

    def add_assistant_response(self, response: ChatResponse) -> None:
        if response.tool_calls or response.content:
            serialized = _serialize_assistant_message(response)
            self._messages.append(serialized)

    def add_tool_result(self, tool_call_id: str, content: str) -> None:
        self._messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        })

    def estimate_tokens(self) -> int:
        return estimate_tokens(self._messages)

    def check_and_compact(self) -> bool:
        """Compact context if approaching limit. Returns True if compaction occurred."""
        if needs_compaction(self._messages, max_tokens=self.max_tokens):
            self._messages = compact_messages(self._messages)
            return True
        return False
