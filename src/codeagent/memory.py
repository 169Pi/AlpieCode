"""
Memory — persistent cross-session context for AlpieCode.

Saves key learnings from each session to ~/.alpiecode/memories/:
  - Project structure and layout
  - Build/test commands discovered
  - Coding patterns and conventions
  - Known issues and workarounds

Memories are loaded at the start of each new session and injected
into the system prompt as additional context.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import List, Optional

MEMORY_DIR = Path.home() / ".alpiecode" / "memories"


def _project_key(workdir: Path) -> str:
    """Generate a stable key for a project directory."""
    return hashlib.md5(str(workdir.resolve()).encode()).hexdigest()[:12]


def _memory_path(workdir: Path) -> Path:
    """Get the memory file path for a project."""
    return MEMORY_DIR / f"{_project_key(workdir)}.json"


def load_memories(workdir: Path) -> List[dict]:
    """
    Load memories for a specific project directory.

    Returns:
        List of memory entries, each with 'content', 'timestamp', 'type'
    """
    path = _memory_path(workdir)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data.get("memories", [])
    except (json.JSONDecodeError, KeyError):
        return []


def save_memories_batch(workdir: Path, entries: List[dict]) -> None:
    """
    Save multiple memory entries for a project in a single atomic disk write.

    Args:
        workdir: Project directory
        entries: List of dicts, each with 'content' and optional 'type'
    """
    if not entries:
        return

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = _memory_path(workdir)

    existing = load_memories(workdir)
    existing_contents = {m.get("content") for m in existing}
    now = time.time()
    workdir_str = str(workdir.resolve())

    added = False
    for entry in entries:
        c = entry.get("content", "").strip()
        if not c or c in existing_contents:
            continue
        existing.append({
            "content": c,
            "type": entry.get("type", "learning"),
            "timestamp": now,
            "workdir": workdir_str,
        })
        existing_contents.add(c)
        added = True

    if not added:
        return

    # Keep only the last 20 memories per project (FIFO)
    if len(existing) > 20:
        existing = existing[-20:]

    path.write_text(json.dumps({
        "project": workdir_str,
        "memories": existing,
    }, indent=2))


def save_memory(workdir: Path, content: str, memory_type: str = "learning") -> None:
    """
    Save a single memory entry for a project.

    Args:
        workdir: Project directory
        content: The memory content to save
        memory_type: Type of memory (learning, structure, command, pattern)
    """
    save_memories_batch(workdir, [{"content": content, "type": memory_type}])


def format_memories_for_prompt(workdir: Path) -> Optional[str]:
    """
    Format memories into a string suitable for injection into the system prompt.

    Returns:
        Formatted memories string, or None if no memories exist
    """
    memories = load_memories(workdir)
    if not memories:
        return None

    lines = ["## Recalled memories from previous sessions on this project:\n"]
    for mem in memories[-10:]:  # Only inject last 10 to save context
        lines.append(f"- [{mem.get('type', 'note')}] {mem['content']}")

    lines.append(
        "\nNote: These memories are from previous sessions. "
        "Verify they are still accurate before relying on them."
    )
    return "\n".join(lines)


def extract_and_save_memories(workdir: Path, messages: list) -> None:
    """
    After a session ends, extract key learnings from the conversation
    and save them as memories in a single atomic batch.

    Scans tool results for commonly useful information like:
    - Successful build/test commands
    - Project structure (from list_files results)
    - Completion summaries
    """
    to_save: List[dict] = []
    saved_cmds = set()  # Avoid duplicate command memories

    for idx, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue

        # ── Save successful build/test commands ──
        if msg.get("role") == "tool":
            content = msg.get("content", "")
            if '"exit_code": 0' in content:
                # Walk backwards to find the bash tool_call that produced this result
                tool_call_id = msg.get("tool_call_id", "")
                for prev in reversed(messages[:idx]):
                    if prev.get("role") == "assistant" and prev.get("tool_calls"):
                        for tc in prev["tool_calls"]:
                            tc_dict = tc if isinstance(tc, dict) else {}
                            if tc_dict.get("id") == tool_call_id:
                                fn = tc_dict.get("function", {})
                                if fn.get("name") == "bash":
                                    try:
                                        args = fn.get("arguments", "{}")
                                        if isinstance(args, str):
                                            args = json.loads(args)
                                        cmd = args.get("command", "")
                                    except (json.JSONDecodeError, AttributeError):
                                        cmd = ""
                                    if cmd and cmd not in saved_cmds:
                                        if any(kw in cmd for kw in ["pytest", "test", "unittest", "npm run test", "cargo test", "go test"]):
                                            to_save.append({"content": f"Working test command: {cmd}", "type": "command"})
                                            saved_cmds.add(cmd)
                                        elif any(kw in cmd for kw in ["build", "compile", "g++", "gcc", "make", "cargo build", "npm run build"]):
                                            to_save.append({"content": f"Working build command: {cmd}", "type": "command"})
                                            saved_cmds.add(cmd)
                        break

            # ── Save project structure from list_files / tree output ──
            if "├" in content or "└" in content:
                if len(content) < 2000:
                    to_save.append({"content": f"Project structure:\n{content[:500]}", "type": "structure"})

        # ── Save completion summaries ──
        if msg.get("role") == "assistant" and msg.get("content"):
            content = msg["content"]
            if content.strip().startswith("DONE"):
                to_save.append({"content": content.strip()[:200], "type": "completion_summary"})

    if to_save:
        save_memories_batch(workdir, to_save)
