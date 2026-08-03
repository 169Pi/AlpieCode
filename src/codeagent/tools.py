"""
Tool definitions and implementations for AlpieCode.

11 tools total:
  Files:   read_file, write_file, edit_file, list_files, file_search, apply_patch
  Execute: bash
  Web:     web_search, fetch_url
  Agent:   request_user_input, update_plan
"""

import json
import os
import re
import subprocess
import textwrap
from pathlib import Path
from typing import Optional

from .guardian import gate_command

# ── Tool schemas (OpenAI function-calling format) ─────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "Run a shell command in the repo working directory. Returns stdout/stderr/exit_code. "
                "Prefer file tools (read_file, edit_file) over shell for reading/writing files. "
                "Use this for running tests, builds, git commands, and other CLI operations."
            ),
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
            "description": "Read a file's contents with line numbers, optionally restricted to a line range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file from repo root"},
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
            "description": (
                "Replace one exact occurrence of old_str with new_str in a file. "
                "The old_str must match exactly (including whitespace/indentation). "
                "You must read_file first before editing."
            ),
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
            "description": "List files in the repository tree (respects .gitignore). Returns file paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Subdirectory to list (default: repo root)"},
                    "max_depth": {"type": "integer", "description": "Max directory depth (default: 4)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_search",
            "description": (
                "Search for a pattern across files in the repository using regex or literal matching. "
                "Returns matching lines with file paths and line numbers. Like ripgrep/grep."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Search pattern (regex or literal string)"},
                    "path": {"type": "string", "description": "Subdirectory to search in (default: repo root)"},
                    "include": {"type": "string", "description": "File glob pattern to include (e.g., '*.py')"},
                    "case_insensitive": {"type": "boolean", "description": "Case-insensitive search (default: false)"},
                },
                "required": ["pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_patch",
            "description": (
                "Apply a unified diff patch to a file. The patch should be in standard unified diff format "
                "with --- and +++ headers, @@ hunk markers, and +/- line prefixes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file to patch"},
                    "patch": {"type": "string", "description": "Unified diff content to apply"},
                },
                "required": ["path", "patch"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for information. Returns relevant results with titles, URLs, and snippets. "
                "Use for looking up documentation, error messages, API references, etc."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "num_results": {"type": "integer", "description": "Number of results (default: 5, max: 10)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch and extract text content from a URL. Returns the page content as plain text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_user_input",
            "description": (
                "Ask the user a clarifying question when the task is ambiguous or you need "
                "a decision before proceeding. Returns the user's response."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "The question to ask the user"},
                },
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_plan",
            "description": (
                "Write or update a structured task plan. Call this before making edits to document "
                "what you intend to do, which files will be changed, and how you'll verify success."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "plan": {
                        "type": "string",
                        "description": "The structured plan: deliverables, files to change, and verification checks",
                    },
                },
                "required": ["plan"],
            },
        },
    },
]


# ── Tool implementations ──────────────────────────────────────────────

def _build_venv_env(workdir: Path) -> dict:
    """Build an environment dict with .venv/bin prepended to PATH."""
    env = os.environ.copy()
    venv_bin = workdir / ".venv" / "bin"
    if venv_bin.is_dir():
        env["PATH"] = str(venv_bin) + ":" + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(workdir / ".venv")
        # Remove PYTHONHOME if set — it breaks venvs
        env.pop("PYTHONHOME", None)
    return env


def _bash(workdir: Path, command: str) -> str:
    """Run a shell command with guardian safety gate.

    Uses /bin/bash (not /bin/sh) and auto-activates .venv if present.
    """
    if not gate_command(command, auto_approve=True):
        return json.dumps({
            "stdout": "",
            "stderr": "Command blocked by safety gate. Run it manually if needed.",
            "exit_code": -1,
        })
    try:
        env = _build_venv_env(workdir)
        result = subprocess.run(
            ["bash", "-c", command],
            cwd=workdir, capture_output=True, text=True, timeout=120, env=env,
        )
        return json.dumps({
            "stdout": result.stdout[-4000:],
            "stderr": result.stderr[-2000:],
            "exit_code": result.returncode,
        })
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
    total = len(lines)
    if start_line is not None:
        lines = lines[start_line - 1 : end_line if end_line else None]
    numbered = [f"{i + (start_line or 1):4d} | {line}" for i, line in enumerate(lines)]
    result = "\n".join(numbered)
    if start_line is not None:
        result += f"\n\n[Showing lines {start_line}-{end_line or total} of {total} total]"
    return result


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
        return "error: old_str not found in file. Make sure it matches exactly (including whitespace)."
    if count > 1:
        return f"error: old_str matched {count} times, need exactly 1 match. Use a more specific old_str."
    p.write_text(text.replace(old_str, new_str, 1))
    return "edit applied"


def _list_files(workdir: Path, path: str = ".", max_depth: int = 4) -> str:
    target = workdir / path
    if not target.exists():
        return f"error: path not found: {path}"

    # Try git ls-files first
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=target, capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            files = result.stdout.strip().splitlines()
            filtered = [f for f in files if f.count(os.sep) < max_depth]
            if filtered:
                return "\n".join(sorted(filtered[:200]))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Fallback: os.walk
    entries = []
    for root, dirs, files in os.walk(target):
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


def _file_search(workdir: Path, pattern: str, path: str = ".", include: str = None,
                 case_insensitive: bool = False) -> str:
    """Search for a pattern across files using grep."""
    target = workdir / path

    # Build grep command
    cmd = ["grep", "-rn", "--color=never"]
    if case_insensitive:
        cmd.append("-i")
    if include:
        cmd.extend(["--include", include])
    # Exclude common non-code directories
    for excl in [".git", "node_modules", "__pycache__", ".venv", "venv", ".egg-info"]:
        cmd.extend(["--exclude-dir", excl])
    cmd.extend([pattern, str(target)])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=workdir)
        output = result.stdout.strip()
        if not output:
            return f"No matches found for pattern: {pattern}"

        lines = output.splitlines()
        if len(lines) > 50:
            return "\n".join(lines[:50]) + f"\n\n... ({len(lines) - 50} more matches)"
        return output
    except subprocess.TimeoutExpired:
        return "error: search timed out after 30s"
    except FileNotFoundError:
        return "error: grep not available on this system"


def _apply_patch(workdir: Path, path: str, patch: str) -> str:
    """Apply a unified diff patch to a file."""
    target = workdir / path
    if not target.exists():
        return f"error: file not found: {path}"

    try:
        # Write patch to temp file and apply
        patch_file = workdir / ".alpiecode_patch.tmp"
        # Ensure patch has proper file headers
        full_patch = patch
        if not patch.startswith("---"):
            full_patch = f"--- a/{path}\n+++ b/{path}\n{patch}"
        patch_file.write_text(full_patch)

        result = subprocess.run(
            ["patch", "-p1", "--no-backup-if-mismatch", "-i", str(patch_file)],
            cwd=workdir, capture_output=True, text=True, timeout=10
        )
        patch_file.unlink(missing_ok=True)

        if result.returncode == 0:
            return f"patch applied successfully to {path}"
        else:
            return f"error applying patch: {result.stderr or result.stdout}"
    except FileNotFoundError:
        # Fallback: manual line-by-line patch application
        patch_file = workdir / ".alpiecode_patch.tmp"
        patch_file.unlink(missing_ok=True)
        return "error: 'patch' command not available. Use edit_file instead."
    except Exception as e:
        patch_file = workdir / ".alpiecode_patch.tmp"
        patch_file.unlink(missing_ok=True)
        return f"error applying patch: {e}"


def _web_search(query: str, num_results: int = 5) -> str:
    """Search the web using DuckDuckGo (no API key needed)."""
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=min(num_results, 10)))
        if not results:
            return f"No results found for: {query}"
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"{i}. **{r.get('title', 'No title')}**\n   URL: {r.get('href', '')}\n   {r.get('body', '')}")
        return "\n\n".join(formatted)
    except ImportError:
        return "error: web search unavailable — install duckduckgo-search package"
    except Exception as e:
        return f"error during web search: {e}"


def _fetch_url(url: str) -> str:
    """Fetch and extract text content from a URL."""
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "AlpieCode/0.2.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # Try to extract text with beautifulsoup if available
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            # Remove script and style elements
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
        except ImportError:
            # Fallback: basic HTML tag stripping
            text = re.sub(r"<[^>]+>", "", html)
            text = re.sub(r"\s+", " ", text).strip()

        # Truncate to reasonable length
        if len(text) > 8000:
            text = text[:8000] + f"\n\n... (truncated, {len(text)} chars total)"
        return text
    except Exception as e:
        return f"error fetching URL: {e}"


def _request_user_input(question: str) -> str:
    """Ask the user a question and return their response."""
    try:
        from rich.console import Console
        from rich.panel import Panel
        console = Console()
        console.print(Panel(
            f"[bold]{question}[/bold]",
            title="❓ Agent needs your input",
            border_style="yellow",
        ))
        response = console.input("[bold green]Your answer ❯[/bold green] ").strip()
    except ImportError:
        print(f"\n❓ Agent needs your input: {question}")
        response = input("Your answer ❯ ").strip()

    return response or "(no response)"


def _update_plan(workdir: Path, plan: str) -> str:
    """Save the agent's task plan to a file."""
    plan_path = workdir / ".alpiecode_plan.md"
    plan_path.write_text(f"# AlpieCode Task Plan\n\n{plan}\n")
    return f"plan saved to .alpiecode_plan.md"


# ── Dispatch factory ──────────────────────────────────────────────────

def make_dispatch(workdir: Path):
    """Bind tool implementations to a specific working directory."""
    return {
        "bash": lambda a: _bash(workdir, a["command"]),
        "read_file": lambda a: _read_file(workdir, a["path"], a.get("start_line"), a.get("end_line")),
        "write_file": lambda a: _write_file(workdir, a["path"], a["content"]),
        "edit_file": lambda a: _edit_file(workdir, a["path"], a["old_str"], a["new_str"]),
        "list_files": lambda a: _list_files(workdir, a.get("path", "."), a.get("max_depth", 4)),
        "file_search": lambda a: _file_search(workdir, a["pattern"], a.get("path", "."),
                                               a.get("include"), a.get("case_insensitive", False)),
        "apply_patch": lambda a: _apply_patch(workdir, a["path"], a["patch"]),
        "web_search": lambda a: _web_search(a["query"], a.get("num_results", 5)),
        "fetch_url": lambda a: _fetch_url(a["url"]),
        "request_user_input": lambda a: _request_user_input(a["question"]),
        "update_plan": lambda a: _update_plan(workdir, a["plan"]),
    }
