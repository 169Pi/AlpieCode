"""
Unit tests verifying Phase 1 stability fixes:
- BUG-01: executor.py dead code removal
- BUG-02: cli.py duplicate command handler removal
- BUG-04: orchestrator.py verification nudge state leak prevention
- BUG-06: orchestrator.py backend immutability / thread safety
- BUG-09: tools.py bash timeout error message alignment
- BUG-11: compaction.py tool-call pairing integrity
"""
import ast
from pathlib import Path
from unittest.mock import MagicMock, patch
import json
import pytest

from codeagent.executor import ToolExecutor, ToolCall, ToolResult
from codeagent.compaction import compact_messages, KEEP_RECENT_TURNS
from codeagent.orchestrator import AgentOrchestrator
from codeagent.session import SessionManager
from codeagent.config import Config
from codeagent.backends.base import ChatResponse
from codeagent.backends.openai_backend import OpenAIBackend
from codeagent.backends.local_backend import LocalBackend


def test_bug01_executor_dead_code_removed():
    """Verify executor.py no longer contains the unreachable sequential execution block."""
    executor_path = Path(__file__).resolve().parent.parent / "src" / "codeagent" / "executor.py"
    content = executor_path.read_text(encoding="utf-8")
    assert "# Sequential execution" not in content
    assert content.count("return results") == 0


def test_bug01_executor_execution():
    """Verify ToolExecutor correctly executes tool calls via the DAG pipeline."""
    workdir = Path("/tmp")
    executor = ToolExecutor(workdir)

    def dummy_tool(args):
        return f"result: {args.get('x', 0)}"

    executor.dispatch["dummy_tool"] = dummy_tool

    calls = [
        ToolCall(id="c1", name="dummy_tool", arguments={"x": 42}),
        ToolCall(id="c2", name="dummy_tool", arguments={"x": 99}),
    ]

    results = executor.execute_tool_calls(calls)
    assert len(results) == 2
    assert results[0].tool_call_id == "c1"
    assert "result: 42" in results[0].content
    assert results[1].tool_call_id == "c2"
    assert "result: 99" in results[1].content


def test_bug02_cli_no_duplicate_handlers():
    """Verify cli.py has exactly one diff and one doctor handler."""
    cli_path = Path(__file__).resolve().parent.parent / "src" / "codeagent" / "cli.py"
    content = cli_path.read_text(encoding="utf-8")
    
    assert content.count('args.command == "diff"') == 1
    assert content.count('args.command == "doctor"') == 1


def test_bug04_and_06_orchestrator_state_isolation(tmp_path):
    """Verify orchestrator does not leak verification_nudge on self and does not mutate self.backend."""
    mock_backend = MagicMock(spec=["name", "is_available", "chat_completion"])
    mock_backend.name = "MockOpenAI"
    mock_backend.is_available = True
    mock_backend.chat_completion.return_value = ChatResponse(
        content="DONE: Task is finished",
        reasoning=None,
        tool_calls=[],
    )

    orchestrator = AgentOrchestrator(backend=mock_backend)
    session_mgr = SessionManager()
    session = session_mgr.create_session(workdir=tmp_path, max_tokens=8192)
    cfg = Config()

    # Before run
    assert not hasattr(orchestrator, "_verification_nudge")
    original_backend = orchestrator.backend

    events = list(orchestrator.run_task(session=session, task="Simple test task", cfg=cfg))

    # After run: verify _verification_nudge is NOT set on orchestrator instance
    assert not hasattr(orchestrator, "_verification_nudge")
    # Verify backend on orchestrator was NOT mutated
    assert orchestrator.backend is original_backend

    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1


def test_bug06_fallback_preserves_orchestrator_backend(tmp_path):
    """Verify that when online backend fails and falls back to local, self.backend is NOT mutated."""
    mock_openai = MagicMock(spec=OpenAIBackend)
    mock_openai.name = "OpenAI"
    mock_openai.is_available = True
    mock_openai.chat_completion.side_effect = ConnectionError("Online service unreachable")
    # Disallow stream so it hits chat_completion directly
    del mock_openai.chat_completion_stream

    orchestrator = AgentOrchestrator(backend=mock_openai)
    session_mgr = SessionManager()
    session = session_mgr.create_session(workdir=tmp_path, max_tokens=8192)
    cfg = Config()

    fallback_resp = ChatResponse(
        content="DONE: Handled by local fallback",
        reasoning=None,
        tool_calls=[],
    )

    with patch.object(LocalBackend, "__init__", return_value=None), \
         patch.object(LocalBackend, "chat_completion", return_value=fallback_resp):
        events = list(orchestrator.run_task(session=session, task="Fallback test", cfg=cfg))

    event_types = [e.type for e in events]
    assert "fallback" in event_types
    assert "done" in event_types

    # Critical check: orchestrator.backend must still be the original OpenAI backend!
    assert orchestrator.backend is mock_openai


def test_orchestrator_streaming(tmp_path):
    """Verify orchestrator handles streaming backends properly."""
    mock_backend = MagicMock(spec=["name", "is_available", "chat_completion", "chat_completion_stream"])
    mock_backend.name = "MockStreamBackend"
    mock_backend.is_available = True
    
    chat_resp = ChatResponse(
        content="DONE: Stream completed",
        reasoning="thinking about stream",
        tool_calls=[],
    )
    mock_backend.chat_completion_stream.return_value = iter([
        ("token", {"delta": "DONE: "}),
        ("token", {"delta": "Stream completed"}),
        ("done", chat_resp),
    ])

    orchestrator = AgentOrchestrator(backend=mock_backend)
    session_mgr = SessionManager()
    session = session_mgr.create_session(workdir=tmp_path, max_tokens=8192)
    cfg = Config()

    events = list(orchestrator.run_task(session=session, task="Streaming test", cfg=cfg))
    event_types = [e.type for e in events]
    assert "token" in event_types
    assert "done" in event_types


def test_bug09_bash_timeout_message(tmp_path):
    """Verify tools.py _bash returns 120s timeout in error message."""
    import subprocess
    from codeagent.tools import _bash

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="sleep 200", timeout=120)):
        res = _bash(tmp_path, "sleep 200")
        data = json.loads(res)
        assert data["exit_code"] == -1
        assert "120s" in data["stderr"]
        assert "300s" not in data["stderr"]


def test_bug11_compaction_tool_pairing_guard():
    """Verify compact_messages does not split an assistant tool-call from its tool results."""
    # Build a message list where KEEP_RECENT_TURNS would land right on a tool message
    messages = [
        {"role": "system", "content": "You are AlpieCode."},
        {"role": "user", "content": "Initial prompt"},
        {"role": "assistant", "content": "Thinking about step 1..."},
        {"role": "user", "content": "Continue"},
    ]

    # Add several turns of assistant + tool calls
    for i in range(10):
        call_id = f"call_{i}"
        messages.append({
            "role": "assistant",
            "content": f"Running tool {i}",
            "tool_calls": [{"id": call_id, "function": {"name": "read_file", "arguments": "{}"}}]
        })
        messages.append({
            "role": "tool",
            "tool_call_id": call_id,
            "content": f"file content {i}"
        })

    compacted = compact_messages(messages)
    assert len(compacted) > 0
    assert compacted[0]["role"] == "system"

    # In compacted messages, every 'tool' message must be immediately preceded by
    # an 'assistant' message that contains its tool_call_id or another 'tool' from the same assistant
    for idx, msg in enumerate(compacted):
        if msg.get("role") == "tool":
            prev_msg = compacted[idx - 1]
            assert prev_msg.get("role") in ("assistant", "tool"), (
                f"Tool message at index {idx} was preceded by role '{prev_msg.get('role')}'"
            )
