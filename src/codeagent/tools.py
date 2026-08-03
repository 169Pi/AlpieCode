"""
Tool definitions and implementations for codeagent.

Each tool is defined as an OpenAI-compatible function schema and has
a corresponding Python implementation that operates on a working directory.
"""

import json
import os
import subprocess
from pathlib import Path

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command in the repo working directory. Returns stdout/stderr/exit_code.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "The shell command to execute"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file's contents, optionally restricted to a line range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file from the repo root"},
                    "start_line": {"type": "integer", "description": "First line to read (1-indexed)"},
                    "end_line": {"type": "integer", "description": "Last line to read (1-indexed, inclusive)"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file with the given content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"},
                    "content": {"type": "string", "description": "The full content to write"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace one exact occurrence of old_str with new_str in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"},
                    "old_str": {"type": "string", "description": "Exact string to find (must match exactly once)"},
                    "new_str": {"type": "string", "description": "Replacement string"},
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List all files in the repository directory tree (respects .gitignore). "
                           "Returns a tree-style listing of file paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Subdirectory to list (relative to repo root). Defaults to '.' (entire repo).",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum directory depth to traverse. Defaults to 4.",
                    },
                },
                "required": [],
            },
        },
    },
]


# ── Tool implementations ──────────────────────────────────────────────

def _bash(workdir: Path, command: str) -> str:
    try:
        result = subprocess.run(
            command, shell=True, cwd=workdir, capture_output=True, text=True, timeout=120
        )
        return json.dumps(
            {
                "stdout": result.stdout[-4000:],
                "stderr": result.stderr[-2000:],
                "exit_code": result.returncode,
            }
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"stdout": "", "stderr": "Command timed out after 120s", "exit_code": -1})


def _read_file(workdir: Path, path: str, start_line: int = None, end_line: int = None) -> str:
    target = workdir / path
    if not target.exists():
        return f"error: file not found: {path}"
    if not target.is_file():
        return f"error: not a file: {path}"
    try:
        lines = target.read_text(errors="replace").splitlines()
    except Exception as e:
        return f"error reading file: {e}"
    if start_line is not None:
        lines = lines[start_line - 1 : end_line if end_line else None]
    numbered = [f"{i + (start_line or 1):4d} | {line}" for i, line in enumerate(lines)]
    return "\n".join(numbered)


def _write_file(workdir: Path, path: str, content: str) -> str:
    p = workdir / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return f"wrote {len(content)} bytes to {path}"


def _edit_file(workdir: Path, path: str, old_str: str, new_str: str) -> str:
    p = workdir / path
    if not p.exists():
        return f"error: file not found: {path}"
    text = p.read_text()
    count = text.count(old_str)
    if count == 0:
        return "error: old_str not found in file"
    if count > 1:
        return f"error: old_str matched {count} times, need exactly 1 match"
    p.write_text(text.replace(old_str, new_str, 1))
    return "edit applied"


def _list_files(workdir: Path, path: str = ".", max_depth: int = 4) -> str:
    """List files using git ls-files if available, otherwise walk the directory."""
    target = workdir / path
    if not target.exists():
        return f"error: path not found: {path}"

    # Try git ls-files first (respects .gitignore)
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=target, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            files = result.stdout.strip().splitlines()
            # Filter by max_depth
            filtered = []
            for f in files:
                depth = f.count(os.sep)
                if depth < max_depth:
                    filtered.append(f)
            if filtered:
                return "\n".join(sorted(filtered[:200]))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: os.walk
    entries = []
    for root, dirs, files in os.walk(target):
        # Skip hidden dirs
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        rel_root = os.path.relpath(root, target)
        depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
        if depth >= max_depth:
            dirs.clear()
            continue
        for fname in sorted(files):
            if fname.startswith("."):
                continue
            rel_path = os.path.join(rel_root, fname) if rel_root != "." else fname
            entries.append(rel_path)
    return "\n".join(entries[:200]) or "(empty directory)"


def make_dispatch(workdir: Path):
    """Bind tool implementations to a specific working directory."""
    return {
        "bash": lambda a: _bash(workdir, a["command"]),
        "read_file": lambda a: _read_file(workdir, a["path"], a.get("start_line"), a.get("end_line")),
        "write_file": lambda a: _write_file(workdir, a["path"], a["content"]),
        "edit_file": lambda a: _edit_file(workdir, a["path"], a["old_str"], a["new_str"]),
        "list_files": lambda a: _list_files(workdir, a.get("path", "."), a.get("max_depth", 4)),
    }
