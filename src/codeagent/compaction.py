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
  - Generate structured conversation summaries and extract relevant history
    for the decoupled ContextManager build_context() pipeline.
"""

import json
from typing import Any, Dict, List, Optional

# Our model's context window
MAX_CONTEXT_TOKENS = 262_144
# Start compacting when we hit this percentage of the context window
COMPACT_THRESHOLD = 0.70
# Number of recent turns to always keep intact
KEEP_RECENT_TURNS = 12
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
            elif isinstance(content, list):
                total_chars += sum(len(str(c)) for c in content)
            # Account for tool call arguments
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                for tc in tool_calls:
                    if isinstance(tc, dict):
                        fn = tc.get("function", {})
                        total_chars += len(str(fn.get("arguments", "")))
                        total_chars += len(str(fn.get("name", "")))
    return total_chars // CHARS_PER_TOKEN


def needs_compaction(messages: List[dict], max_tokens: int = MAX_CONTEXT_TOKENS) -> bool:
    """Check if the conversation needs compaction."""
    tokens = estimate_tokens(messages)
    return tokens > (max_tokens * COMPACT_THRESHOLD)


def _summarize_tool_result(tool_name: str, content: str) -> str:
    """Create a compact summary of a tool result."""
    # NEVER truncate the execution plan — it's critical architectural context
    if tool_name == "update_plan":
        return content

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


def extract_conversation_summary(
    messages: List[dict],
    metadata: Optional[List[dict]] = None,
) -> str:
    """
    Extract a concise, structured markdown summary of historical turns.

    Extracts:
      - Initial user task / goal
      - Key files created, edited, or inspected
      - Commands executed and their success/failure
      - Execution plan status
      - Crucial findings or errors encountered
    """
    if not messages:
        return ""

    initial_task = ""
    files_touched = set()
    commands_run = []
    latest_plan = ""
    key_events = []

    for i, msg in enumerate(messages):
        role = msg.get("role", "")
        content = msg.get("content") or ""

        # Extract initial goal from first non-system user message
        if role == "user" and not initial_task:
            if isinstance(content, str) and content.strip():
                lines = content.strip().splitlines()
                initial_task = lines[0][:150]
                if len(lines[0]) > 150:
                    initial_task += "..."

        # Assistant tool calls
        if role == "assistant" and msg.get("tool_calls"):
            for tc in msg.get("tool_calls", []):
                tc_dict = tc if isinstance(tc, dict) else {}
                fn = tc_dict.get("function", {})
                name = fn.get("name", "")
                args_raw = fn.get("arguments", "{}")
                try:
                    args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                except Exception:
                    args = {}

                if name in ("write_file", "patch_file", "read_file"):
                    p = args.get("path") or args.get("file_path")
                    if p:
                        files_touched.add(f"{name}:{p}")
                elif name == "bash":
                    cmd = args.get("command", "")
                    if cmd:
                        commands_run.append(cmd[:80])

        # Tool outputs
        if role == "tool":
            content_str = str(content)
            if "[Plan updated]" in content_str or "Plan Status:" in content_str or "## Implementation Plan" in content_str:
                latest_plan = content_str[-500:]  # Keep latest plan snapshot
            elif "exit_code" in content_str and '"exit_code": 0' not in content_str:
                # Capture error indication
                key_events.append("Command execution returned an error (addressed in subsequent turns)")

    summary_lines = []
    if initial_task:
        summary_lines.append(f"- **Initial Goal**: {initial_task}")
    if files_touched:
        files_preview = ", ".join(list(files_touched)[:6])
        if len(files_touched) > 6:
            files_preview += f" (+{len(files_touched) - 6} more)"
        summary_lines.append(f"- **Files Touched**: {files_preview}")
    if commands_run:
        recent_cmds = ", ".join(commands_run[-4:])
        summary_lines.append(f"- **Recent Commands Executed**: {recent_cmds}")
    if latest_plan:
        summary_lines.append(f"- **Execution Plan Snapshot**:\n  {latest_plan.strip()}")
    if key_events:
        summary_lines.append(f"- **Notes**: {key_events[-1]}")

    if not summary_lines:
        return ""

    return "### Conversation Progress Summary (Prior Turns):\n" + "\n".join(summary_lines)


def select_relevant_history(
    messages: List[dict],
    metadata: Optional[List[dict]] = None,
    current_query: str = "",
    token_budget: int = 2048,
) -> str:
    """
    Select high-value historical anchors from distant history (e.g. plan updates,
    key decisions, important command outcomes) formatted as concise contextual notes.
    """
    if not messages:
        return ""

    high_value_notes = []
    seen_plans = set()

    # Search backwards for high-importance messages
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        role = msg.get("role", "")
        content = str(msg.get("content") or "")

        # High priority: update_plan outputs
        if role == "tool" and ("[Plan updated]" in content or "Plan Status:" in content):
            if "plan" not in seen_plans:
                seen_plans.add("plan")
                lines = [l.strip() for l in content.splitlines() if l.strip() and not l.startswith("```")]
                snippet = "\n".join(lines[:8])
                high_value_notes.append(f"- **Active Plan Anchor**:\n{snippet}")

        # High priority: stall advice or system corrections
        if role == "user" and ("[STALL DETECTED]" in content or "[SYSTEM]" in content):
            high_value_notes.append(f"- **System Intervention**: {content[:200]}")

        # If we have enough context, stop
        total_len = sum(len(n) for n in high_value_notes)
        if (total_len // CHARS_PER_TOKEN) >= token_budget:
            break

    if not high_value_notes:
        return ""

    return "### Relevant Historical Anchors:\n" + "\n".join(reversed(high_value_notes))


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

    # ── Tool-Call Pairing Guard ──
    # If cutoff lands on a 'tool' message, move it backwards to include
    # the preceding 'assistant' message that owns the tool_call_id.
    # This prevents OpenAI API 400 errors ("missing tool result for tool_call_id").
    min_cutoff = 1 if system else 0
    while cutoff > min_cutoff and messages[cutoff].get("role") == "tool":
        cutoff -= 1

    old_messages = messages[1:cutoff] if system else messages[:cutoff]
    recent_messages = messages[cutoff:]

    # Build a compacted summary of old messages
    compacted_old = []

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
