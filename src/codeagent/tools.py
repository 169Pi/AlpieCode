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
                "Use this for running tests, builds, git commands, and other CLI operations. "
                "IMPORTANT: Commands run WITHOUT a TTY (no terminal). Interactive programs, "
                "ncurses/curses apps, TUI apps, and terminal games will NOT work — they produce "
                "garbage output or hang. Do NOT attempt to run interactive programs through this tool. "
                "For interactive apps, verify correctness via: clean compilation + code review instead."
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
    {
        "type": "function",
        "function": {
            "name": "view_image",
            "description": (
                "Inspect an image file (.png, .jpg, .jpeg, .webp, .gif, .svg) in the repository. "
                "Encodes and returns image description / metadata for visual analysis."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the image file"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_issues",
            "description": (
                "Fetch issues and pull requests from a GitHub repository. "
                "Can list issues or get full details of a specific issue including comments. "
                "Use this to understand bugs, feature requests, and discussions in open-source projects."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner (e.g., 'pytorch')"},
                    "repo": {"type": "string", "description": "Repository name (e.g., 'pytorch')"},
                    "issue_number": {"type": "integer", "description": "Specific issue number to get full details (optional)"},
                    "state": {"type": "string", "description": "Filter by state: 'open', 'closed', or 'all' (default: 'open')"},
                    "max_results": {"type": "integer", "description": "Max issues to return (default: 10, max: 30)"},
                },
                "required": ["owner", "repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_browse",
            "description": (
                "Browse a GitHub repository's structure, files, and metadata without cloning. "
                "Can list directory contents or read a specific file directly from GitHub. "
                "Use this for quick exploration before deciding whether to clone."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "owner": {"type": "string", "description": "Repository owner (e.g., 'facebook')"},
                    "repo": {"type": "string", "description": "Repository name (e.g., 'react')"},
                    "path": {"type": "string", "description": "File or directory path to browse (default: root)"},
                    "info_only": {"type": "boolean", "description": "If true, return only repo metadata (stars, description, etc.)"},
                },
                "required": ["owner", "repo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "clone_repo",
            "description": (
                "Clone a GitHub repository into the working directory for deep analysis, editing, and testing. "
                "Use github_browse first for quick exploration; only clone when you need to make edits or run tests. "
                "Clones with --depth 1 (shallow) to save time and disk space."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_url": {
                        "type": "string",
                        "description": "GitHub repo URL or owner/repo shorthand (e.g., 'pytorch/pytorch' or 'https://github.com/pytorch/pytorch')",
                    },
                    "branch": {"type": "string", "description": "Branch to clone (default: main/master)"},
                },
                "required": ["repo_url"],
            },
        },
    },
]


# ── Tool implementations ──────────────────────────────────────────────

def _build_venv_env(workdir: Path) -> dict:
    """Build an environment dict with .venv/bin (or .venv/Scripts on Windows) prepended to PATH."""
    env = os.environ.copy()
    venv_bin = workdir / ".venv" / ("Scripts" if os.name == "nt" else "bin")
    if not venv_bin.is_dir():
        venv_bin = workdir / ".venv" / ("bin" if os.name == "nt" else "Scripts")
    if venv_bin.is_dir():
        path_sep = ";" if os.name == "nt" else ":"
        env["PATH"] = str(venv_bin) + path_sep + env.get("PATH", "")
        env["VIRTUAL_ENV"] = str(workdir / ".venv")
        env.pop("PYTHONHOME", None)
    return env


def _smart_truncate(text: str, max_chars: int = 6000) -> str:
    """Truncate long output keeping both head and tail (where errors usually are).

    Compiler errors appear at the top (file:line: error: ...) while the
    bottom often has summary counts. Keeping both ends gives the model
    far better error visibility than tail-only truncation.
    """
    if len(text) <= max_chars:
        return text
    head_size = int(max_chars * 0.6)  # 60% head — where real errors live
    tail_size = max_chars - head_size  # 40% tail — summaries and counts
    omitted = len(text) - head_size - tail_size
    return (
        text[:head_size]
        + f"\n\n... [{omitted} chars omitted] ...\n\n"
        + text[-tail_size:]
    )



def _extract_script_path(command: str) -> str:
    """Extract the script file path from a bash command, if any."""
    import re as _re
    patterns = [
        r"python3?\s+(?:-[a-zA-Z]+\s+)*([^\s|>&;]+\.py)",
        r"node\s+([^\s|>&;]+\.js)",
        r"ruby\s+([^\s|>&;]+\.rb)",
        r"\./([^\s|>&;]+)",
        r"bash\s+([^\s|>&;]+\.sh)",
    ]
    for pat in patterns:
        m = _re.search(pat, command)
        if m:
            return m.group(1)
    return ""


def _bash(workdir: Path, command: str) -> str:
    """Run a shell command with guardian safety gate.

    Cross-platform support for Linux, macOS, and native Windows.
    """
    # ── Offline-aware command interception ────────────────────────────
    if getattr(_bash, '_offline_mode', False):
        # Block package install commands when offline (no internet)
        install_patterns = ['pip install', 'uv pip install', 'uv add', 'npm install', 'apt install', 'apt-get install']
        cmd_lower = command.lower().strip()
        for pattern in install_patterns:
            if pattern in cmd_lower:
                return json.dumps({
                    "stdout": "",
                    "stderr": f"⚠️ OFFLINE MODE: '{pattern}' blocked — no internet available. Use only standard library modules.",
                    "exit_code": 1,
                })
        # Auto-replace pytest with unittest
        if 'pytest' in command or '-m pytest' in command:
            command = command.replace('python -m pytest', 'python -m unittest')
            command = command.replace('pytest', 'python -m unittest')

    if not gate_command(command, auto_approve=True):
        return json.dumps({
            "stdout": "",
            "stderr": "Command blocked by safety gate. Run it manually if needed.",
            "exit_code": -1,
        })
    try:
        import shutil
        env = _build_venv_env(workdir)

        # Cross-platform shell resolution
        if shutil.which("bash"):
            shell_cmd = ["bash", "-c", command]
        elif os.name == "nt":
            if shutil.which("powershell"):
                shell_cmd = ["powershell", "-NoProfile", "-Command", command]
            else:
                shell_cmd = ["cmd.exe", "/c", command]
        else:
            shell_cmd = ["/bin/sh", "-c", command]

        result = subprocess.run(
            shell_cmd,
            cwd=workdir, capture_output=True, text=True,
            stdin=subprocess.DEVNULL,
            timeout=30, env=env,
        )

        stdout = _smart_truncate(result.stdout, 6000)
        stderr = _smart_truncate(result.stderr, 4000)

        output = json.dumps({
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
        })

        # ── Smart Guardrail 1: Failed command — inject actionable hints ──
        if result.returncode != 0:
            script_file = _extract_script_path(command)
            hint = (
                f"⚠️ COMMAND FAILED (exit_code={result.returncode}). "
                f"Read the error output carefully and fix the ROOT CAUSE.\n"
            )
            if script_file:
                hint += (
                    f"💡 HINT: Use read_file to examine \'{script_file}\' around the "
                    f"failing line before making edits. Do NOT guess — read first.\n"
                )
            output = hint + output

        # ── Smart Guardrail 2: Silent success — script ran but no output ──
        elif result.returncode == 0 and not stdout.strip() and not stderr.strip():
            script_file = _extract_script_path(command)
            if script_file:
                output += (
                    "\n\n⚠️ WARNING: Command succeeded (exit_code=0) but produced "
                    "NO OUTPUT. This usually means:\n"
                    "  1. The main execution block (if __name__ == \'__main__\') is missing or broken\n"
                    "  2. An exception is being silently caught with a bare \'except: pass\'\n"
                    "  3. The print/output statements were accidentally removed\n"
                    f"→ Use read_file to check \'{script_file}\' — especially the main block "
                    "at the bottom of the file. Do NOT re-run the same command."
                )

        return output
    except subprocess.TimeoutExpired:
        return json.dumps({"stdout": "", "stderr": "Command timed out after 300s", "exit_code": -1})


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
    """Search the web using DDGS (DuckDuckGo)."""
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
            
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=min(num_results, 10)))
        if not results:
            return (
                f"No web results found for '{query}'. "
                "Tip: If searching for Python package documentation, use bash: python -c 'import pkg; help(pkg)'"
            )
        formatted = []
        for i, r in enumerate(results, 1):
            formatted.append(f"{i}. **{r.get('title', 'No title')}**\n   URL: {r.get('href', '')}\n   {r.get('body', '')}")
        return "\n\n".join(formatted)
    except ImportError:
        return "error: web search unavailable — install ddgs or duckduckgo-search package"
    except Exception as e:
        return f"error during web search: {e}. Tip: Try python -c 'help(...)' for installed library docs."


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


def _view_image(workdir: Path, path: str) -> str:
    """Inspect and return metadata + base64 data for an image file."""
    target = workdir / path
    if not target.exists():
        return f"error: image file not found: {path}"
    
    import base64
    ext = target.suffix.lower().lstrip(".")
    mime_type = f"image/{'jpeg' if ext in ('jpg', 'jpeg') else ext}"
    
    try:
        size = target.stat().st_size
        encoded = base64.b64encode(target.read_bytes()).decode("utf-8")
        # Truncate string for string representation, model will get image context
        return f"[Image {path} | Type: {mime_type} | Size: {size} bytes | Base64 Length: {len(encoded)}]"
    except Exception as e:
        return f"error reading image: {e}"


# ── GitHub tool implementations ───────────────────────────────────────

def _github_issues(owner: str, repo: str, issue_number: int = None,
                   state: str = "open", max_results: int = 10) -> str:
    """Fetch issues/PRs from a GitHub repo."""
    from .github import fetch_issues, fetch_issue_detail
    if issue_number:
        return fetch_issue_detail(owner, repo, issue_number)
    return fetch_issues(owner, repo, state=state, max_results=max_results)


def _github_browse(owner: str, repo: str, path: str = "",
                   info_only: bool = False) -> str:
    """Browse a GitHub repo's structure and files."""
    from .github import fetch_repo_info, fetch_repo_tree
    if info_only:
        return fetch_repo_info(owner, repo)
    if path:
        return fetch_repo_tree(owner, repo, path)
    # Return repo info + root tree
    info = fetch_repo_info(owner, repo)
    tree = fetch_repo_tree(owner, repo)
    return f"=== Repository Info ===\n{info}\n\n=== Root Directory ===\n{tree}"


def _clone_repo(workdir: Path, repo_url: str, branch: str = None) -> str:
    """Clone a GitHub repo into the workdir."""
    from .github import clone_repo
    return clone_repo(repo_url, workdir, branch=branch)


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
        "view_image": lambda a: _view_image(workdir, a["path"]),
        "github_issues": lambda a: _github_issues(
            a["owner"], a["repo"],
            issue_number=a.get("issue_number"),
            state=a.get("state", "open"),
            max_results=a.get("max_results", 10),
        ),
        "github_browse": lambda a: _github_browse(
            a["owner"], a["repo"],
            path=a.get("path", ""),
            info_only=a.get("info_only", False),
        ),
        "clone_repo": lambda a: _clone_repo(
            workdir, a["repo_url"],
            branch=a.get("branch"),
        ),
    }
