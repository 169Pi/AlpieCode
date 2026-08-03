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


def save_memory(workdir: Path, content: str, memory_type: str = "learning") -> None:
    """
    Save a memory entry for a project.

    Args:
        workdir: Project directory
        content: The memory content to save
        memory_type: Type of memory (learning, structure, command, pattern)
    """
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = _memory_path(workdir)

    existing = load_memories(workdir)
    existing.append({
        "content": content,
        "type": memory_type,
        "timestamp": time.time(),
        "workdir": str(workdir.resolve()),
    })

    # Keep only the last 20 memories per project (FIFO)
    if len(existing) > 20:
        existing = existing[-20:]

    path.write_text(json.dumps({
        "project": str(workdir.resolve()),
        "memories": existing,
    }, indent=2))


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
    and save them as memories.

    This scans tool results for commonly useful information like:
    - Project structure (from list_files results)
    - Test commands (from bash results running tests)
    - Build commands (from bash results running builds)
    """
    for msg in messages:
        if not isinstance(msg, dict):
            continue

        # Look for tool results
        if msg.get("role") == "tool":
            content = msg.get("content", "")

            # Detect test commands that succeeded
            if '"exit_code": 0' in content and any(kw in content.lower() for kw in
                    ["pytest", "test", "passed", "ok", "success"]):
                # Find the corresponding tool call to get the command
                pass  # Would need more context to extract command

        # Look for assistant messages with DONE
        if msg.get("role") == "assistant" and msg.get("content"):
            content = msg["content"]
            if content.strip().startswith("DONE"):
                save_memory(workdir, content.strip()[:200], "completion_summary")
