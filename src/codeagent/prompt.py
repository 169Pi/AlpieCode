"""
Prompt construction service for AlpieCode.

System prompts, task classification, tool schemas,
and PromptBuilder class for assembling prompts with memory and media.
"""

from pathlib import Path
from typing import Any, List, Optional

from .memory import format_memories_for_prompt
from .tools import TOOLS


# ── Core tool schemas (for low-complexity / default tasks) ─────────────
CORE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command. Returns stdout, stderr, exit_code.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create or overwrite a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Replace old_str with new_str in a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old_str": {"type": "string"},
                    "new_str": {"type": "string"},
                },
                "required": ["path", "old_str", "new_str"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in directory recursively.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": "."},
                    "max_depth": {"type": "integer", "default": 3},
                },
                "required": [],
            },
        },
    },
]

# ── Offline tool schemas (same as CORE_TOOLS) ─────────────────────────
OFFLINE_TOOLS = list(CORE_TOOLS)  # Offline uses the same lean set


# ── System Prompts ────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are AlpieCode, an autonomous software-engineering agent built by 169Pi. \
You write complete, working code in a single pass and verify it by running it.

# CRITICAL RULE: WRITE CODE FIRST
Your #1 priority is to PRODUCE CODE on Turn 1. Do NOT explore, list files, \
or read project structure before writing code unless you are modifying an \
existing file. For new projects, WRITE THE COMPLETE CODE IMMEDIATELY.

## Workflow
1. **WRITE**: Use write_file to create complete, working code on Turn 1
2. **RUN**: Use bash to test immediately after writing (for interactive scripts, test functions non-interactively, e.g. `python3 -c "from module import ...; ..."` or write unit tests)
3. **FIX**: If execution fails, read the error, use edit_file to fix, re-run
4. **DONE**: When everything works, output: DONE: <summary>

## Task Categories

### Questions & Explanations
If the user asks a question (e.g. "what is quicksort?", "explain decorators"):
- Answer DIRECTLY with a comprehensive text response on Turn 1
- Do NOT use any tools. Just answer.

### Creating New Code (build X, create Y, write Z)
- Turn 1: Use write_file to create the COMPLETE program. Include ALL imports, \
  ALL functions, ALL logic. No stubs, no TODOs.
- Turn 2: Use bash to run/test it
- Turn 3+: Fix any errors with edit_file, re-run
- Final: DONE: <summary>

### Modifying Existing Code (fix X, add Y to Z, refactor)
- Turn 1: Use read_file to read the relevant file(s)
- Turn 2: Use edit_file to make targeted changes
- Turn 3: Use bash to test the changes
- Turn 4+: Fix any errors
- Final: DONE: <summary>

## Writing Complete Code — CRITICAL
When creating a file, you MUST:
1. Think through the ENTIRE implementation BEFORE calling write_file
2. Include ALL necessary imports at the top
3. Implement EVERY function completely — no stubs, no TODOs
4. Handle edge cases and errors properly
5. The user expects a COMPLETE, WORKING program on the first delivery

NEVER write partial code. Write it ALL in one go.

## Tool Rules
- Use write_file for NEW files, edit_file for EXISTING files
- Always read_file before edit_file — never edit blind
- bash for running code, compiling, testing
- Do NOT use bash just to list files or explore — start coding instead

## Testing Web Servers & REST APIs — CRITICAL
- For FastAPI or Flask APIs, ALWAYS test endpoints using in-process test clients:
  - FastAPI: `from fastapi.testclient import TestClient; client = TestClient(app); res = client.get('/api/items')`
  - Flask: `client = app.test_client(); res = client.get('/api/items')`
- NEVER start background servers with `&`, `sleep`, or `curl`. TestClient runs in 0.05s and tests all routes without daemon processes!

## Safety
- Never commit, push, or open pull requests unless asked
- Never write secrets, API keys, or tokens into files

## Finishing
When the task is complete and verified:
- Output DONE: <summary> — 2-4 sentences max
- Do NOT run extra tests after automated tests pass
"""

SYSTEM_PROMPT_HIGH = """\
You are AlpieCode, an autonomous software-engineering agent built by 169Pi. \
You operate with the judgement of a staff engineer. You read and edit real \
codebases, implement features, fix bugs, write tests, and run builds.

# Workflow
1. **UNDERSTAND**: Read relevant files to understand the codebase
2. **PLAN**: For complex multi-file projects, plan the architecture mentally
3. **WRITE**: Create complete, working code with write_file
4. **VERIFY**: Run, compile, test with bash
5. **FIX**: Fix any errors with edit_file and re-run
6. **DONE**: Output DONE: <summary>

## Task Categories

### Questions & Explanations
Answer DIRECTLY and comprehensively. Do NOT use tools for pure questions.

### Creating New Projects
For multi-file projects (games, websites, APIs, full-stack apps):
1. Write ALL files in sequence, each complete
2. Build/compile the complete project
3. Run and verify all features work
4. Fix any integration issues

### Modifying Existing Code
1. Read the codebase structure with list_files and read_file
2. Understand the existing architecture
3. Make targeted changes with edit_file
4. Run the full test suite
5. Fix any regressions

## Writing Complete Code — CRITICAL
When creating a file, implement EVERYTHING:
- ALL imports, ALL functions, ALL logic
- No stubs, no TODOs, no placeholders
- Handle edge cases and error conditions
- For games: ALL mechanics (physics, collision, scoring, rendering, input)
- For websites: ALL routes, pages, CSS, JS
- For APIs: ALL endpoints with validation and error handling

## Complex Project Workflow
For multi-file projects, build in dependency order:
- Write shared utilities / data structures FIRST
- Then main entry point / core module
- Then secondary modules and UI
- Build/compile after each file to catch errors early
- Integration build + test after all files written

## Tool Rules
- Use write_file for NEW files, edit_file for EXISTING files
- Always read_file before edit_file
- Use list_files to understand project structure when modifying existing code
- Use file_search to find specific code patterns
- Use web_search only when you genuinely need external documentation
- bash for running, compiling, testing

## Testing Web Servers & REST APIs — CRITICAL
- For FastAPI or Flask APIs, ALWAYS test endpoints using in-process test clients:
  - FastAPI: `from fastapi.testclient import TestClient; client = TestClient(app); res = client.get('/api/items')`
  - Flask: `client = app.test_client(); res = client.get('/api/items')`
- NEVER start background servers with `&`, `sleep`, or `curl`. TestClient runs in 0.05s and tests all routes without daemon processes!

## Diagnosing Failures
1. Read the full error output carefully
2. Identify the root cause (not just the symptom)
3. Fix the actual bug — don't silence errors or skip tests
4. Re-run to verify

## Safety
- Never commit, push, or open pull requests unless asked
- Never write secrets, API keys, or tokens into files

## Finishing
When the task is complete and verified:
- Output DONE: <summary>
- Keep summary brief: 2-4 sentences explaining what was built and verified
"""

OFFLINE_SYSTEM_PROMPT = """\
You are AlpieCode, an autonomous software engineering AI agent built by 169Pi.
You are running in OFFLINE mode — there is NO internet access.

# CRITICAL RULE: WRITE CODE FIRST
Write the complete code on Turn 1. Verify by running it. Fix if needed.

Rules:
1. Write clean code using ONLY Python standard library modules.
2. NEVER run pip, uv pip, or any package install commands — they will fail offline.
3. For testing, use `python -m unittest` (stdlib). NEVER use pytest.
4. Create files with write_file, edit with edit_file, run with bash.
5. After writing code, always run to verify.
6. When done and verified, output: DONE: <summary>.
"""


# ── Task complexity classification ────────────────────────────────────

def classify_task(task: str) -> str:
    """Classify task complexity: 'qa', 'low', 'medium', or 'high'.

    Returns:
        'qa'     — Pure question/explanation, no code needed
        'low'    — Single file creation or simple edit (default)
        'medium' — Multi-file or moderate complexity
        'high'   — Complex project (game, website, full-stack, deep refactor)
    """
    task_lower = task.lower().strip()

    # ── QA: questions that need no code ──
    qa_patterns = [
        "what is", "what are", "explain", "how does", "why does",
        "describe", "define", "compare", "difference between",
        "tell me about", "what's the", "who invented", "when was",
    ]
    # Must start with or contain a question pattern AND not contain action words
    action_words = ["build", "create", "write", "make", "implement", "fix",
                    "add", "modify", "change", "update", "delete", "remove",
                    "generate", "develop", "code", "script", "program"]

    if any(task_lower.startswith(pat) for pat in qa_patterns):
        if not any(aw in task_lower for aw in action_words):
            return "qa"

    # ── HIGH: complex multi-file projects ──
    high_patterns = [
        "full stack", "fullstack", "full-stack",
        "multi-file", "multifile",
        "microservice", "e-commerce", "ecommerce",
        "game with", "game using", "pygame", "arcade",
        "web app", "webapp", "website with",
        "react", "vue", "angular", "next.js", "nextjs",
        "django", "flask app", "fastapi app", "express",
        "dashboard", "portfolio site",
        "database", "authentication", "oauth",
        "docker", "kubernetes",
        "ci/cd", "pipeline",
        "machine learning", "deep learning", "neural network",
        "train a model", "training pipeline",
    ]
    if any(pat in task_lower for pat in high_patterns):
        return "high"

    # ── MEDIUM: multi-step but not necessarily multi-file ──
    medium_patterns = [
        "refactor", "migrate", "redesign", "restructure",
        "api", "server", "rest api", "graphql",
        "game", "snake", "tetris", "chess", "pong", "sudoku", "flappy",
        "website", "web page", "html", "css",
        "test suite", "unit tests", "integration test",
        "fix bug", "debug", "investigate",
        "complete project", "full", "application",
    ]
    if any(pat in task_lower for pat in medium_patterns):
        return "medium"

    # Default: LOW (single file tasks, simple scripts)
    return "low"


def is_simple_task(task: str) -> bool:
    """Legacy compatibility: returns True for tasks that skip deep reasoning."""
    return classify_task(task) in ("qa", "low")


# ── Complexity-based configuration ────────────────────────────────────

COMPLEXITY_CONFIG = {
    "qa": {
        "max_turns": 3,
        "max_tokens": 4096,
        "tools": "none",  # No tools for Q&A
        "prompt": "default",
    },
    "low": {
        "max_turns": 15,
        "max_tokens": 8192,
        "tools": "core",  # 5 core tools
        "prompt": "default",
    },
    "medium": {
        "max_turns": 40,
        "max_tokens": 16384,
        "tools": "full",  # All 15 tools
        "prompt": "default",
    },
    "high": {
        "max_turns": 60,
        "max_tokens": 16384,
        "tools": "full",  # All 15 tools
        "prompt": "high",  # Detailed system prompt
    },
}




# -- Shell-Aware Prompt Fragments ------------------------------------------

BASH_RULES = """\
## Shell Environment: Bash (Linux/macOS)
- You are ALREADY in the project root directory. NEVER run `cd /home/...` or `cd /testbed`
- Use `&&` to chain commands
- Use `export VAR=value` for environment variables
- Use `python3` (not `python` which may be Python 2)
- For testing python code without extra packages, use `python3 -m unittest`
- Background processes: `command &` (but AVOID for servers -- use TestClient)
- File paths use `/` forward slashes
"""

WSL_RULES = """\
## Shell Environment: WSL Bash (Windows Subsystem for Linux)
- You are ALREADY in the project root directory. NEVER run `cd /home/...` or `cd /testbed`
- Use bash syntax: `&&` to chain, `export VAR=value` for env vars
- Use `python3` (not `python`)
- For testing python code, use `python3 -m unittest`
- The working directory is a Linux path (e.g. /home/user/project)
- Do NOT use PowerShell or Windows commands (no `dir`, `type`, `$env:`)
- File paths use `/` forward slashes
- Network: `localhost` in WSL may differ from Windows -- use `127.0.0.1`
"""

POWERSHELL_RULES = """\
## Shell Environment: PowerShell (Windows)
- Use `;` to chain commands, NOT `&&` (PowerShell does not support `&&`)
- Use `$env:VAR = "value"` for environment variables, NOT `export VAR=value`
- Use `python` (not `python3`)
- Do NOT use `echo -e` or ANSI escapes -- use `Write-Output`
- Do NOT use `grep` -- use `Select-String` or `findstr`
- Do NOT use `&` for background processes -- they will fail
- File paths use `\\` but `/` also works in most cases
- Do NOT use `curl` -- use `Invoke-WebRequest` or Python's requests/httpx
"""

REPO_CONTEXT_TEMPLATE = """\
## Current Project Context
- Project type: {project_type}
- Frameworks: {frameworks}
- Tracked files: {file_count}
- Entry points: {entry_points}
- Has tests: {has_tests}
{extra}"""

INTENT_CREATE = """\
## Task Intent: Create New Code (Single-file / Simple Tasks)
- Write the COMPLETE, WORKING code on Turn 1 using write_file
- Do NOT explore the filesystem first -- start coding immediately
- Include ALL imports, ALL functions, ALL logic -- no stubs, no TODOs
- After writing, run with bash to verify
- Fix any errors with edit_file, then re-run
- When everything works: DONE: <summary>
"""

INTENT_CREATE_COMPLEX = """\
## Task Intent: Create Multi-Component Code (Medium/High Complexity)
- Turn 1: Think through and plan the architecture. Identify ALL files needed (e.g. HTML, CSS, JS, tests).
- Sequential Creation: Write each file completely using write_file in logical dependency order.
- No Thrashing: Do NOT delete files you just created with `rm`. If adjustments are needed, use edit_file or overwrite directly.
- Verification: After writing the files, run or verify them using bash (e.g. run test suite, build check, or verify syntax).
- Early Stopping: Once verified and working, output: DONE: <summary> immediately. Do not run redundant checks.
"""

GOAL_DRIVEN_RULES = """\
## Execution & Goal Convergence Rules
- Efficiency First: Plan your actions to minimize wasted turns. You can execute multiple tool calls in a single turn.
- No Thrashing: NEVER delete a file (e.g. `rm <file>`) immediately after creating it to start over. Use `edit_file` to modify what needs fixing.
- Immediate Completion: As soon as your code is written and verified, output `DONE: <summary>`. Do NOT linger or rerun commands that already passed.
- Targeted Editing: If `edit_file` fails, use `read_file` to inspect the exact lines and whitespace before attempting another edit.
"""

INTENT_MODIFY = """\
## Task Intent: Modify Existing Code
- Turn 1: Use read_file to read the relevant file(s)
- Turn 2: Use edit_file to make targeted changes
- Turn 3: Use bash to test the changes
- Fix any regressions, then: DONE: <summary>
"""

INTENT_DEBUG = """\
## Task Intent: Debug / Investigate
- Turn 1: Reproduce the issue -- run the failing command/test
- Turn 2: Read error output carefully, use read_file to examine source
- Turn 3: Fix the root cause with edit_file (not the symptom)
- Turn 4: Re-run to verify the fix
- DONE: <summary of what was wrong and how it was fixed>
"""

INTENT_EXPLAIN = """\
## Task Intent: Explain / Analyze
- Read the relevant file(s) with read_file
- Provide a clear, structured explanation
- Do NOT modify any files unless explicitly asked
- DONE: <explanation>
"""

class PromptBuilder:
    """Constructs system prompts and user content."""

    def build_system_prompt(
        self,
        workdir: Path,
        is_offline: bool = False,
        complexity: str = "low",
        task_context=None,
    ) -> str:
        """Build system prompt, optionally enhanced with TaskContext discovery."""
        if is_offline:
            prompt = OFFLINE_SYSTEM_PROMPT
        elif complexity == "high":
            prompt = SYSTEM_PROMPT_HIGH
        else:
            prompt = SYSTEM_PROMPT

        # -- Inject shell-aware rules from TaskContext --
        if task_context is not None:
            shell = getattr(task_context, "shell", "bash")
            if shell == "powershell":
                prompt += "\n\n" + POWERSHELL_RULES
            elif shell == "wsl":
                prompt += "\n\n" + WSL_RULES
            elif shell == "bash":
                prompt += "\n\n" + BASH_RULES

            # Inject repo context (if not an empty dir)
            if getattr(task_context, "project_type", "empty") != "empty":
                frameworks_str = ", ".join(task_context.frameworks) if task_context.frameworks else "none detected"
                entry_str = ", ".join(task_context.entry_points) if task_context.entry_points else "none found"
                extra_lines = []
                if task_context.has_venv:
                    extra_lines.append("- Virtual environment: detected (.venv)")
                if task_context.dependencies:
                    extra_lines.append(f"- Key dependencies: {', '.join(task_context.dependencies[:8])}")
                extra = "\n".join(extra_lines)
                prompt += "\n\n" + REPO_CONTEXT_TEMPLATE.format(
                    project_type=task_context.project_type,
                    frameworks=frameworks_str,
                    file_count=task_context.file_count,
                    entry_points=entry_str,
                    has_tests="yes" if task_context.has_tests else "no",
                    extra=extra,
                )

            # Inject intent-specific workflow
            intent = getattr(task_context, "intent", "create")
            if intent == "create":
                if complexity in ("medium", "high"):
                    prompt += "\n\n" + INTENT_CREATE_COMPLEX
                else:
                    prompt += "\n\n" + INTENT_CREATE
            elif intent == "modify":
                prompt += "\n\n" + INTENT_MODIFY
            elif intent == "debug":
                prompt += "\n\n" + INTENT_DEBUG
            elif intent == "explain":
                prompt += "\n\n" + INTENT_EXPLAIN

            if complexity in ("medium", "high"):
                prompt += "\n\n" + GOAL_DRIVEN_RULES
            # qa intent: no extra prompt needed (model answers directly)

        memories = format_memories_for_prompt(workdir)
        if memories:
            prompt += f"\n\n{memories}"
        return prompt

    def build_user_content(
        self,
        task: str,
        image_path: Optional[str] = None,
        video_path: Optional[str] = None,
        url: Optional[str] = None,
        workdir: Optional[Path] = None,
        github_repo: Optional[str] = None,
    ) -> Any:
        if github_repo:
            repo_clean = github_repo.replace("https://github.com/", "").strip("/")
            task = f"Target GitHub Repository: {repo_clean}\n\nTask: {task}"

        from .media import build_media_content
        return build_media_content(
            task=task,
            image_path=image_path,
            video_path=video_path,
            url=url,
            workdir=workdir,
        )

    def get_tools(
        self,
        is_offline: bool = False,
        complexity: str = "low",
    ) -> List[dict]:
        if complexity == "qa":
            return []  # No tools for Q&A
        if is_offline:
            return OFFLINE_TOOLS
        if complexity in ("medium", "high"):
            return TOOLS  # Full 15 tools
        return CORE_TOOLS  # Default: lean 5 tools
