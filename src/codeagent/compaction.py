"""
Context compaction for AlpieCode.

When the conversation history approaches the model's context window limit,
this module summarizes older turns to free up space while preserving
the essential information needed for the agent to continue working.

Strategy:
  - Keep system prompt and last N turns intact
  - Summarize older tool calls and results into compact descriptions
  - Preserve all user messages verbatim
  - Track approximate token count using a simple heuristic (4 chars ≈ 1 token)
"""

import json
from typing import List

# Our model's context window
MAX_CONTEXT_TOKENS = 262_144
# Start compacting when we hit this percentage of the context window
COMPACT_THRESHOLD = 0.70
# Number of recent turns to always keep intact
KEEP_RECENT_TURNS = 10
# Approximate chars per token (rough heuristic)
CHARS_PER_TOKEN = 4


def estimate_tokens(messages: List[dict]) -> int:
    """Estimate token count from a list of messages."""
    total_chars = 0
    for msg in messages:
        if isinstance(msg, dict):
            content = msg.get("content") or ""
            if isinstance(content, str):
                total_chars += len(content)
            # Account for tool call arguments
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        fn = tc.get("function", {})
                        total_chars += len(fn.get("arguments", ""))
                        total_chars += len(fn.get("name", ""))
    return total_chars // CHARS_PER_TOKEN


def needs_compaction(messages: List[dict]) -> bool:
    """Check if the conversation needs compaction."""
    tokens = estimate_tokens(messages)
    return tokens > (MAX_CONTEXT_TOKENS * COMPACT_THRESHOLD)


def _summarize_tool_result(tool_name: str, content: str) -> str:
    """Create a compact summary of a tool result."""
    if len(content) <= 300:
        return content

    if tool_name == "bash":
        try:
            data = json.loads(content)
            stdout = data.get("stdout", "")
            stderr = data.get("stderr", "")
            exit_code = data.get("exit_code", -1)
            summary = f"exit_code={exit_code}"
            if stdout:
                summary += f", stdout({len(stdout)} chars): {stdout[:150]}..."
            if stderr:
                summary += f", stderr: {stderr[:100]}..."
            return summary
        except json.JSONDecodeError:
            pass

    if tool_name in ("read_file", "list_files"):
        lines = content.splitlines()
        if len(lines) > 20:
            return "\n".join(lines[:10]) + f"\n... ({len(lines) - 20} lines omitted) ...\n" + "\n".join(lines[-10:])

    # Generic truncation
    return content[:250] + f"... ({len(content)} chars total)"


def compact_messages(messages: List[dict]) -> List[dict]:
    """
    Compact a message list by summarizing older turns.

    Preserves:
      - System prompt (index 0)
      - All user messages (verbatim)
      - Last KEEP_RECENT_TURNS messages (verbatim)

    Summarizes:
      - Older tool results (truncated)
      - Older assistant reasoning (removed)
    """
    if len(messages) <= KEEP_RECENT_TURNS + 2:
        return messages

    # Always keep system prompt
    system = messages[0] if messages and messages[0].get("role") == "system" else None

    # Split into old and recent
    cutoff = len(messages) - KEEP_RECENT_TURNS
    old_messages = messages[1:cutoff] if system else messages[:cutoff]
    recent_messages = messages[cutoff:]

    # Build a compacted summary of old messages
    compacted_old = []
    summary_parts = []

    for msg in old_messages:
        role = msg.get("role", "")

        if role == "user":
            # Keep user messages verbatim
            compacted_old.append(msg)

        elif role == "assistant":
            # Compact assistant messages: keep tool calls but remove reasoning
            compact_msg = {"role": "assistant"}
            if msg.get("content"):
                # Truncate long assistant content
                content = msg["content"]
                if len(content) > 200:
                    compact_msg["content"] = content[:200] + "..."
                else:
                    compact_msg["content"] = content
            else:
                compact_msg["content"] = None

            if msg.get("tool_calls"):
                compact_msg["tool_calls"] = msg["tool_calls"]
            compacted_old.append(compact_msg)

        elif role == "tool":
            # Summarize tool results
            tool_call_id = msg.get("tool_call_id", "")
            content = msg.get("content", "")

            # Try to find the tool name from the preceding assistant message
            tool_name = "unknown"
            for prev in reversed(compacted_old):
                if prev.get("tool_calls"):
                    for tc in prev["tool_calls"]:
                        tc_dict = tc if isinstance(tc, dict) else {}
                        if tc_dict.get("id") == tool_call_id:
                            tool_name = tc_dict.get("function", {}).get("name", "unknown")
                            break
                    break

            compacted_old.append({
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": _summarize_tool_result(tool_name, content),
            })

    # Rebuild message list
    result = []
    if system:
        result.append(system)
    result.extend(compacted_old)
    result.extend(recent_messages)

    return result
