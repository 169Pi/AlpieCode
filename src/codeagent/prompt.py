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
        "max_turns": 10,
        "max_tokens": 8192,
        "tools": "core",  # 5 core tools
        "prompt": "default",
    },
    "medium": {
        "max_turns": 20,
        "max_tokens": 8192,
        "tools": "full",  # All 15 tools
        "prompt": "default",
    },
    "high": {
        "max_turns": 40,
        "max_tokens": 16384,
        "tools": "full",  # All 15 tools
        "prompt": "high",  # Detailed system prompt
    },
}


class PromptBuilder:
    """Constructs system prompts and user content."""

    def build_system_prompt(
        self,
        workdir: Path,
        is_offline: bool = False,
        complexity: str = "low",
    ) -> str:
        if is_offline:
            prompt = OFFLINE_SYSTEM_PROMPT
        elif complexity == "high":
            prompt = SYSTEM_PROMPT_HIGH
        else:
            prompt = SYSTEM_PROMPT

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
