"""
Unit tests verifying Phase 3 performance optimizations:
- PERF-01: context.py distant summary lazy caching
- PERF-06: tools.py _list_files directory pruning and early termination
- PERF-05: memory.py batched disk writes and deduplication
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from codeagent.context import ContextManager
from codeagent.backends.base import ChatResponse, ToolCall
from codeagent.tools import _list_files
import codeagent.memory as memory_mod


# ==============================================================================
# PERF-01: Distant summary lazy caching
# ==============================================================================

def test_perf01_summary_lazy_caching():
    """Verify distant summary is lazy-cached and not re-computed when distant count is unchanged."""
    cm = ContextManager(max_tokens=8192)
    cm.set_system_prompt("Base system prompt")

    # Add 6 turns
    for i in range(6):
        cm.add_user_message(f"User turn {i}")
        cm.add_assistant_response(ChatResponse(
            content=f"Assistant turn {i}",
            reasoning=None,
            tool_calls=[ToolCall(id=f"c_{i}", name="bash", arguments={"command": f"echo {i}"})]
        ))
        cm.add_tool_result(f"c_{i}", f"output {i}", tool_name="bash")

    # First build with recent_turns=2 (creating distant messages)
    context_1 = cm.build_context(recent_turns=2)
    assert cm._cached_summary is not None
    cached_summary = cm._cached_summary
    assert cm._cached_summary_len > 0

    # Next call with same distant turns should reuse the cached summary without calling extract_conversation_summary
    with patch("codeagent.context.extract_conversation_summary", side_effect=RuntimeError("Should NOT be called")):
        context_2 = cm.build_context(recent_turns=2)
        assert context_2 == context_1
        assert cm._cached_summary == cached_summary


# ==============================================================================
# PERF-06: _list_files directory pruning and short-circuit
# ==============================================================================

def test_perf06_list_files_pruning(tmp_path):
    """Verify _list_files prunes node_modules, .venv, __pycache__, and hidden dirs."""
    # Create valid project file
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "index.py").write_text("print('hello')", encoding="utf-8")

    # Create directories that MUST be pruned
    node_modules = tmp_path / "node_modules" / "pkg"
    node_modules.mkdir(parents=True)
    (node_modules / "index.js").write_text("module.exports = {}", encoding="utf-8")

    venv = tmp_path / ".venv" / "lib"
    venv.mkdir(parents=True)
    (venv / "site.py").write_text("# venv file", encoding="utf-8")

    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "index.pyc").write_text("bytes", encoding="utf-8")

    result = _list_files(tmp_path, max_depth=4)

    # Valid file present
    assert "src/index.py" in result or "src\\index.py" in result

    # Pruned directories absent
    assert "node_modules" not in result
    assert ".venv" not in result
    assert "__pycache__" not in result


def test_perf06_list_files_short_circuit(tmp_path):
    """Verify _list_files stops walking after collecting 200 entries."""
    # Create 250 files
    for i in range(250):
        (tmp_path / f"file_{i:03d}.txt").write_text("content", encoding="utf-8")

    result = _list_files(tmp_path, max_depth=2)
    lines = result.splitlines()
    assert len(lines) <= 200


# ==============================================================================
# PERF-05: Batched memory disk writes
# ==============================================================================

def test_perf05_batched_memory_saves(tmp_path, monkeypatch):
    """Verify save_memories_batch performs a single atomic disk update with deduplication and FIFO limits."""
    mem_dir = tmp_path / "memories"
    monkeypatch.setattr(memory_mod, "MEMORY_DIR", mem_dir)

    workdir = tmp_path / "project"
    workdir.mkdir()

    entries = [
        {"content": "Working test command: pytest -v", "type": "command"},
        {"content": "Working build command: npm run build", "type": "command"},
        {"content": "Working test command: pytest -v", "type": "command"},  # Duplicate
    ]

    memory_mod.save_memories_batch(workdir, entries)

    saved = memory_mod.load_memories(workdir)
    assert len(saved) == 2  # Deduplicated from 3 to 2
    contents = [m["content"] for m in saved]
    assert "Working test command: pytest -v" in contents
    assert "Working build command: npm run build" in contents


def test_perf05_extract_and_save_memories_single_batch(tmp_path, monkeypatch):
    """Verify extract_and_save_memories aggregates all discovered items into exactly one batch call."""
    mem_dir = tmp_path / "memories"
    monkeypatch.setattr(memory_mod, "MEMORY_DIR", mem_dir)

    workdir = tmp_path / "project"
    workdir.mkdir()

    messages = [
        {
            "role": "assistant",
            "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": "pytest -v"})}}
            ]
        },
        {
            "role": "tool",
            "tool_call_id": "c1",
            "content": '{"exit_code": 0, "stdout": "All tests passed"}'
        },
        {
            "role": "assistant",
            "content": "DONE: Task completed successfully"
        }
    ]

    with patch.object(memory_mod, "save_memories_batch", wraps=memory_mod.save_memories_batch) as mock_batch:
        memory_mod.extract_and_save_memories(workdir, messages)
        assert mock_batch.call_count == 1
        args, _ = mock_batch.call_args
        assert len(args[1]) == 2  # 1 test command + 1 completion summary
