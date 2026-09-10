"""
Unit tests verifying Phase 2 correctness and resilience fixes:
- BUG-03: context.py context cache and invalidation
- BUG-07: context.py raw history preservation and deep copy
- BUG-08: openai_backend.py partial stream JSON argument repair
- BUG-10: client.py multi-line SSE data accumulation and comment handling
"""

import copy
import io
import json
from unittest.mock import MagicMock, patch
import pytest

from codeagent.context import ContextManager
from codeagent.backends.base import ChatResponse, ToolCall
from codeagent.backends.openai_backend import _repair_and_parse_json_arguments
from codeagent.client import AlpieCodeClient


# ==============================================================================
# BUG-07: Raw history preservation & deep copy
# ==============================================================================

def test_bug07_raw_history_never_mutated_by_rolling_compact():
    """Verify rolling_compact_old_tools truncates working messages while raw_history remains pristine."""
    cm = ContextManager(max_tokens=8192)
    cm.set_system_prompt("System prompt")
    cm.add_user_message("Task 1")

    # Turn 1
    cm.add_assistant_response(ChatResponse(
        content="Running tool",
        reasoning=None,
        tool_calls=[ToolCall(id="call_1", name="bash", arguments={"command": "cat long_file"})]
    ))
    long_tool_output = "\n".join([f"Line {i}: This is long output that should be truncated in compaction." for i in range(50)])
    cm.add_tool_result("call_1", long_tool_output, tool_name="bash")

    # Turn 2
    cm.add_assistant_response(ChatResponse(
        content="Running second tool",
        reasoning=None,
        tool_calls=[ToolCall(id="call_2", name="bash", arguments={"command": "echo done"})]
    ))
    cm.add_tool_result("call_2", "short output", tool_name="bash")

    # Turn 3
    cm.add_assistant_response(ChatResponse(
        content="Final turn",
        reasoning=None,
        tool_calls=[]
    ))

    # Before compaction, verify raw history contains the full 50 lines
    raw_before = cm.all_messages
    tool_msg_raw = [m for m in raw_before if m.get("role") == "tool" and m.get("tool_call_id") == "call_1"][0]
    assert tool_msg_raw["content"] == long_tool_output

    # Run rolling compact keeping only the last turn
    cm.rolling_compact_old_tools(keep_last_turns=1)

    # In active messages, call_1 output should now be truncated
    active_msgs = cm._messages
    tool_msg_active = [m for m in active_msgs if m.get("role") == "tool" and m.get("tool_call_id") == "call_1"][0]
    assert "[Output: 50 lines truncated for brevity]" in tool_msg_active["content"]

    # In all_messages and raw_history, it MUST remain completely intact
    raw_after = cm.all_messages
    tool_msg_raw_after = [m for m in raw_after if m.get("role") == "tool" and m.get("tool_call_id") == "call_1"][0]
    assert tool_msg_raw_after["content"] == long_tool_output

    raw_hist_after = cm.raw_history
    tool_msg_hist_after = [m for m in raw_hist_after if m.get("role") == "tool" and m.get("tool_call_id") == "call_1"][0]
    assert tool_msg_hist_after["content"] == long_tool_output


def test_bug07_raw_history_deep_copy_isolation():
    """Verify mutating dictionaries in the returned raw_history list cannot corrupt ContextManager internals."""
    cm = ContextManager(max_tokens=8192)
    cm.set_system_prompt("System prompt")
    cm.add_user_message("Original user message")

    history = cm.raw_history
    assert len(history) == 2

    # Mutate the returned dictionary
    history[1]["content"] = "CORRUPTED_IN_PLACE"

    # Fetching history again should yield the unmodified original content
    fresh_history = cm.raw_history
    assert fresh_history[1]["content"] == "Original user message"


# ==============================================================================
# BUG-03: Context cache and invalidation
# ==============================================================================

def test_bug03_context_cache_and_invalidation():
    """Verify build_context caches results and invalidates properly on every mutation."""
    cm = ContextManager(max_tokens=8192)
    assert cm._cached_context is None

    cm.set_system_prompt("System prompt")
    cm.add_user_message("User message 1")
    assert cm._cached_context is None

    # First access to messages populates cache
    msgs_1 = cm.messages
    assert cm._cached_context is not None
    cached_ref = cm._cached_context

    # Second access returns cached content without rebuilding
    msgs_2 = cm.messages
    assert msgs_1 == msgs_2
    assert cm._cached_context is cached_ref

    # Adding assistant response must invalidate cache
    cm.add_assistant_response(ChatResponse(content="Response 1", reasoning=None, tool_calls=[]))
    assert cm._cached_context is None

    # Accessing messages repopulates cache
    msgs_3 = cm.messages
    assert len(msgs_3) == 3
    assert cm._cached_context is not None

    # Adding tool result must invalidate cache
    cm.add_tool_result("id_1", "output 1")
    assert cm._cached_context is None

    # Adding user message must invalidate cache
    cm.messages  # populate
    assert cm._cached_context is not None
    cm.add_user_message("User message 2")
    assert cm._cached_context is None

    # Reassigning messages setter must invalidate cache
    cm.messages  # populate
    assert cm._cached_context is not None
    cm.messages = [{"role": "system", "content": "New sys"}]
    assert cm._cached_context is None
    assert len(cm.messages) == 1


# ==============================================================================
# BUG-08: Partial stream JSON argument repair
# ==============================================================================

def test_bug08_partial_json_repair_clean():
    """Verify clean JSON parses directly."""
    res = _repair_and_parse_json_arguments('{"command": "pytest -v", "timeout": 30}')
    assert res == {"command": "pytest -v", "timeout": 30}


def test_bug08_partial_json_repair_truncated_quote_and_brace():
    """Verify truncated JSON missing closing quotes and braces is automatically repaired."""
    # Split mid-string: '{"command": "python -m pytest test.py'
    res = _repair_and_parse_json_arguments('{"command": "python -m pytest test.py')
    assert res == {"command": "python -m pytest test.py"}

    # Missing closing brace only: '{"path": "foo.py", "content": "abc"}'
    res2 = _repair_and_parse_json_arguments('{"path": "foo.py", "content": "abc"')
    assert res2 == {"path": "foo.py", "content": "abc"}


def test_bug08_partial_json_repair_trailing_comma():
    """Verify trailing commas are stripped before parsing."""
    res = _repair_and_parse_json_arguments('{"path": "foo.py",}')
    assert res == {"path": "foo.py"}


def test_bug08_partial_json_repair_python_syntax():
    """Verify Python single-quoted dict strings are parsed via literal_eval."""
    res = _repair_and_parse_json_arguments("{'command': 'ls -la', 'active': True}")
    assert res == {"command": "ls -la", "active": True}


def test_bug08_partial_json_unparseable_preserves_error():
    """Verify completely unparseable input preserves raw arguments and parse error rather than silent empty dict."""
    res = _repair_and_parse_json_arguments("invalid garbage text without json structure")
    assert "_raw_arguments" in res
    assert res["_raw_arguments"] == "invalid garbage text without json structure"
    assert "_parse_error" in res


def test_bug08_partial_json_empty():
    """Verify empty or whitespace string returns empty dict."""
    assert _repair_and_parse_json_arguments("") == {}
    assert _repair_and_parse_json_arguments("   ") == {}


# ==============================================================================
# BUG-10: Multi-line SSE parser accumulation
# ==============================================================================

def test_bug10_multiline_sse_parser():
    """Verify stream_chat correctly accumulates multi-line data fields and ignores comments."""
    # Construct raw SSE stream simulating multi-line JSON payload and SSE comments
    sse_payload = (
        b": keepalive ping\n"
        b"event: message\n"
        b"data: {\"role\": \"assistant\",\n"
        b"data: \"content\": \"hello\\nworld\"}\n"
        b"\n"
        b": another comment\n"
        b"event: token\n"
        b"data: {\"delta\": \" next token\"}\n"
        b"\n"
    )

    mock_resp = MagicMock()
    mock_resp.__enter__.return_value = io.BytesIO(sse_payload)
    mock_resp.__exit__.return_value = False

    client = AlpieCodeClient(base_url="http://localhost:8000")

    with patch("urllib.request.urlopen", return_value=mock_resp):
        events = list(client.stream_chat(task="test multiline"))

    assert len(events) == 2

    # First event: multi-line message
    evt1 = events[0]
    assert evt1.type == "message"
    assert evt1.data["role"] == "assistant"
    assert evt1.data["content"] == "hello\nworld"

    # Second event: token
    evt2 = events[1]
    assert evt2.type == "token"
    assert evt2.data["delta"] == " next token"
