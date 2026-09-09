"""
Conversation context manager for AlpieCode.

Manages the complete conversation history (_messages), message metadata (_metadata),
and dynamically assembles token-budgeted context windows via build_context()
for OpenAI-compatible chat completion endpoints.
"""

import json
import time
from typing import Any, Dict, List, Optional

from .backends.base import ChatResponse, ToolCall
from .compaction import (
    CHARS_PER_TOKEN,
    compact_messages,
    estimate_tokens,
    extract_conversation_summary,
    needs_compaction,
    select_relevant_history,
)


def _serialize_assistant_message(msg: ChatResponse) -> dict:
    """Serialize a ChatResponse into OpenAI chat message dict format."""
    result: Dict[str, Any] = {"role": "assistant"}
    result["content"] = msg.content if msg.content else None

    if msg.tool_calls:
        result["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": json.dumps(tc.arguments) if isinstance(tc.arguments, dict) else str(tc.arguments or "{}"),
                },
            }
            for tc in msg.tool_calls
        ]
    return result


class ContextManager:
    """
    Decoupled context manager maintaining:
      - _messages: Complete, uncompressed OpenAI-compatible message history.
      - _metadata: Parallel metadata tracking per-message (tokens, turn, timestamp, importance, tool info).
      - build_context(): 5-layer context assembly pipeline for OpenAI API calls.
    """

    def __init__(self, max_tokens: int = 262_144):
        self.max_tokens = max_tokens
        self._messages: List[dict] = []
        self._metadata: List[Dict[str, Any]] = []
        self._turn_counter: int = 0
        self._cached_summary: Optional[str] = None

    def _estimate_single_message_tokens(self, msg: dict) -> int:
        """Estimate token count for an individual message."""
        chars = 0
        content = msg.get("content")
        if isinstance(content, str):
            chars += len(content)
        elif isinstance(content, list):
            chars += sum(len(str(c)) for c in content)

        tool_calls = msg.get("tool_calls", [])
        if tool_calls:
            for tc in tool_calls:
                if isinstance(tc, dict):
                    fn = tc.get("function", {})
                    chars += len(str(fn.get("name", "")))
                    chars += len(str(fn.get("arguments", "")))
        return max(1, chars // CHARS_PER_TOKEN)

    def _build_metadata_entry(
        self,
        msg: dict,
        tool_name: Optional[str] = None,
        importance: Optional[str] = None,
        custom: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Construct a structured metadata dict for a message."""
        role = msg.get("role", "unknown")
        tokens = self._estimate_single_message_tokens(msg)
        content_str = str(msg.get("content") or "")

        # Infer tool name if not provided
        resolved_tool_name = tool_name
        if role == "tool" and not resolved_tool_name:
            t_id = msg.get("tool_call_id", "")
            for prev in reversed(self._messages):
                if prev.get("role") == "assistant" and prev.get("tool_calls"):
                    for tc in prev["tool_calls"]:
                        tc_dict = tc if isinstance(tc, dict) else {}
                        if tc_dict.get("id") == t_id:
                            resolved_tool_name = tc_dict.get("function", {}).get("name")
                            break
                    if resolved_tool_name:
                        break

        # Infer importance
        resolved_importance = importance
        if not resolved_importance:
            if role == "system":
                resolved_importance = "high"
            elif role == "user":
                resolved_importance = "high" if "[STALL DETECTED]" in content_str or "[SYSTEM]" in content_str else "normal"
            elif role == "tool":
                if resolved_tool_name == "update_plan" or "[Plan updated]" in content_str or "Plan Status:" in content_str:
                    resolved_importance = "high"
                elif "exit_code" in content_str and '"exit_code": 0' not in content_str:
                    resolved_importance = "high"
                elif resolved_tool_name in ("read_file", "list_files") and len(content_str) > 1000:
                    resolved_importance = "low"
                else:
                    resolved_importance = "normal"
            else:
                resolved_importance = "normal"

        entry: Dict[str, Any] = {
            "turn": self._turn_counter,
            "timestamp": time.time(),
            "role": role,
            "tokens": tokens,
            "tool_name": resolved_tool_name,
            "tool_call_id": msg.get("tool_call_id"),
            "importance": resolved_importance,
            "is_summary": False,
        }
        if custom:
            entry.update(custom)
        return entry

    def _rebuild_metadata(self) -> None:
        """Rebuild _metadata to maintain 1-to-1 sync if _messages is reassigned."""
        self._metadata = [
            self._build_metadata_entry(m) for m in self._messages
        ]

    def set_system_prompt(self, prompt: str) -> None:
        """Set or update the root system prompt (Layer 1)."""
        sys_msg = {"role": "system", "content": prompt}
        if self._messages and self._messages[0].get("role") == "system":
            self._messages[0] = sys_msg
            if self._metadata:
                self._metadata[0] = self._build_metadata_entry(sys_msg, importance="high")
        else:
            self._messages.insert(0, sys_msg)
            self._metadata.insert(0, self._build_metadata_entry(sys_msg, importance="high"))

    def add_user_message(self, content: Any, metadata: Optional[dict] = None) -> None:
        """Append a user request and record metadata."""
        self._turn_counter += 1
        msg = {"role": "user", "content": content}
        self._messages.append(msg)
        self._metadata.append(self._build_metadata_entry(msg, custom=metadata))

    def add_assistant_response(self, response: ChatResponse, metadata: Optional[dict] = None) -> None:
        """Append an assistant response with tool calls and record metadata."""
        if response.tool_calls or response.content:
            msg = _serialize_assistant_message(response)
            self._messages.append(msg)
            tool_names = [tc.name for tc in response.tool_calls] if response.tool_calls else []
            custom_meta = metadata.copy() if metadata else {}
            custom_meta["tool_names"] = tool_names
            custom_meta["has_tools"] = bool(response.tool_calls)
            self._metadata.append(self._build_metadata_entry(msg, custom=custom_meta))

    def add_tool_result(
        self,
        tool_call_id: str,
        content: str,
        tool_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Append a tool execution result and record metadata."""
        msg = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": content,
        }
        self._messages.append(msg)
        self._metadata.append(
            self._build_metadata_entry(msg, tool_name=tool_name, custom=metadata)
        )

    def rolling_compact_old_tools(self, keep_last_turns: int = 3) -> None:
        """
        Truncate large historical tool outputs from turns older than keep_last_turns.
        Preserves update_plan and short outputs.
        """
        assistant_indices = [
            i for i, m in enumerate(self._messages)
            if isinstance(m, dict) and m.get("role") == "assistant"
        ]
        if len(assistant_indices) <= keep_last_turns:
            return

        cutoff_idx = assistant_indices[-keep_last_turns]
        for i in range(cutoff_idx):
            msg = self._messages[i]
            if isinstance(msg, dict) and msg.get("role") == "tool":
                content = str(msg.get("content", ""))
                # Never truncate update_plan output
                if "[Plan updated]" in content or "Plan Status:" in content or len(content) <= 300:
                    continue
                lines = content.splitlines()
                if len(lines) > 8:
                    preview_start = "\n".join(lines[:3])
                    preview_end = "\n".join(lines[-2:])
                    msg["content"] = f"[Output: {len(lines)} lines truncated for brevity]\n{preview_start}\n...\n{preview_end}"
                else:
                    msg["content"] = content[:150] + f"... [truncated {len(content)} chars]"
                # Update tokens in metadata
                if i < len(self._metadata):
                    self._metadata[i]["tokens"] = self._estimate_single_message_tokens(msg)

    def build_context(
        self,
        max_tokens: Optional[int] = None,
        recent_turns: int = 4,
    ) -> List[dict]:
        """
        Assemble the 5-layer context window:
          1. system prompt
          2. summary (of distant turns)
          3. relevant history (high-value anchors)
          4. recent messages (intact tool-call pairs)
          5. current request (tail of conversation)
        """
        if not self._messages:
            return []

        # ── Layer 1: System Prompt ──
        system_msg: Optional[dict] = None
        work_messages: List[dict] = []
        work_metadata: List[dict] = []

        if self._messages[0].get("role") == "system":
            system_msg = dict(self._messages[0])
            work_messages = self._messages[1:]
            work_metadata = self._metadata[1:] if len(self._metadata) > 1 else []
        else:
            work_messages = list(self._messages)
            work_metadata = list(self._metadata)

        if not work_messages:
            return [system_msg] if system_msg else []

        # ── Determine recent turns cutoff ──
        assistant_indices = [
            i for i, m in enumerate(work_messages)
            if isinstance(m, dict) and m.get("role") == "assistant"
        ]

        if len(assistant_indices) <= recent_turns:
            cutoff_idx = 0
        else:
            cutoff_idx = assistant_indices[-recent_turns]

        # ── Ensure Strict OpenAI Tool-Call Pairing Integrity ──
        # If cutoff starts on a 'tool' message, move cutoff backwards to include
        # the preceding 'assistant' message that owns the tool_call_id.
        while cutoff_idx > 0 and work_messages[cutoff_idx].get("role") == "tool":
            cutoff_idx -= 1

        distant_messages = work_messages[:cutoff_idx]
        distant_metadata = work_metadata[:cutoff_idx]
        recent_messages = [dict(m) for m in work_messages[cutoff_idx:]]

        # ── Layer 2 & 3: Summary and Relevant History from Distant Turns ──
        context_blocks = []
        if system_msg:
            context_blocks.append(system_msg)

        if distant_messages:
            # Layer 2: Distant Summary
            summary_text = self._cached_summary or extract_conversation_summary(
                distant_messages, distant_metadata
            )
            # Layer 3: Relevant History Anchors
            relevant_anchors = select_relevant_history(
                distant_messages, distant_metadata
            )

            supplemental_parts = []
            if summary_text:
                supplemental_parts.append(summary_text)
            if relevant_anchors:
                supplemental_parts.append(relevant_anchors)

            if supplemental_parts:
                context_blocks.append({
                    "role": "system",
                    "content": "\n\n".join(supplemental_parts),
                })

        # ── Layer 4 & 5: Recent Messages and Current Request ──
        if len(recent_messages) > 6:
            for i in range(len(recent_messages) - 4):
                m = recent_messages[i]
                if m.get("role") == "tool":
                    c = str(m.get("content") or "")
                    if len(c) > 400 and "[Plan updated]" not in c and "Plan Status:" not in c:
                        lines = c.splitlines()
                        if len(lines) > 8:
                            m["content"] = f"[Output: {len(lines)} lines truncated]\n" + "\n".join(lines[:3]) + "\n...\n" + "\n".join(lines[-2:])
                        else:
                            m["content"] = c[:200] + "... [truncated]"

        context_blocks.extend(recent_messages)

        # ── Budget Verification ──
        effective_limit = max_tokens or self.max_tokens
        if estimate_tokens(context_blocks) > effective_limit:
            context_blocks = compact_messages(context_blocks)

        return context_blocks

    @property
    def messages(self) -> List[dict]:
        """Returns the optimized, context-budgeted messages for model consumption."""
        return self.build_context()

    @messages.setter
    def messages(self, msgs: List[dict]) -> None:
        """Replace messages and rebuild metadata."""
        self._messages = list(msgs)
        self._rebuild_metadata()

    @property
    def all_messages(self) -> List[dict]:
        """Returns the complete, uncompressed historical messages."""
        return list(self._messages)

    @property
    def raw_history(self) -> List[dict]:
        """Alias for all_messages."""
        return list(self._messages)

    @property
    def metadata(self) -> List[Dict[str, Any]]:
        """Returns parallel metadata list for all messages."""
        return list(self._metadata)

    def estimate_tokens(self) -> int:
        """Estimate tokens of the active built context."""
        return estimate_tokens(self.build_context())

    def estimate_total_tokens(self) -> int:
        """Estimate tokens of the entire raw history."""
        return estimate_tokens(self._messages)

    def check_and_compact(self) -> bool:
        """Check if context needs compaction and refresh rolling summary cache."""
        if needs_compaction(self._messages, max_tokens=self.max_tokens):
            self._cached_summary = extract_conversation_summary(self._messages, self._metadata)
            return True
        return False
