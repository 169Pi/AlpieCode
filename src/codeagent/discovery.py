"""
Discovery Engine for AlpieCode -- Zero-LLM Pre-Execution Intelligence.

Runs in under 50ms before the agent turn loop starts. Detects:
  - Task intent (qa, create, modify, debug, explain)
  - Environment (OS, shell, Python version, venv, git)
  - Repository state (project type, frameworks, file count, entry points)
  - Smart complexity (from intent + repo state combined)

All detection is heuristic/filesystem-based -- no LLM calls, no network.
"""

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple


# -- Task Context ----------------------------------------------------------

@dataclass
class TaskContext:
    """Pre-computed intelligence about the task and environment."""

    # Intent
    intent: str = "create"           # qa, create, modify, debug, explain
    complexity: str = "low"          # qa, low, medium, high

    # Environment
    os_name: str = "linux"           # linux, darwin, windows
    shell: str = "bash"             # bash, powershell, cmd, sh, wsl
    python_cmd: str = "python3"     # python3 or python (platform-dependent)
    python_version: str = ""        # e.g. "3.11.2"
    has_venv: bool = False
    has_git: bool = False

    # Repository
    project_type: str = "empty"     # python, node, rust, go, java, empty, unknown
    frameworks: List[str] = field(default_factory=list)
    file_count: int = 0
    has_tests: bool = False
    entry_points: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    # Budget (computed from complexity)
    max_tokens: int = 8192
    tool_set: str = "core"          # none, core, full
    enable_thinking: bool = False


# -- Intent Detection ------------------------------------------------------

# Question patterns -- user wants an answer, not code
_QA_STARTERS = [
    "what is", "what are", "what\'s", "what does", "what do",
    "explain", "how does", "how do", "why does", "why do", "why is",
    "describe", "define", "compare", "difference between",
    "tell me about", "who invented", "who created", "when was",
    "can you explain", "could you explain", "please explain",
    "what\'s the difference", "is it possible", "is there a way",
]

# Action verbs that indicate code generation
_ACTION_VERBS = [
    "build", "create", "write", "make", "implement", "develop",
    "generate", "code", "script", "program", "design", "set up",
    "setup", "scaffold", "bootstrap", "initialize", "init",
]

# Modification verbs
_MODIFY_VERBS = [
    "fix", "add", "modify", "change", "update", "remove", "delete",
    "refactor", "migrate", "upgrade", "downgrade", "rename",
    "move", "restructure", "reorganize", "optimize", "improve",
    "convert", "transform", "replace", "swap",
]

# Debug verbs
_DEBUG_VERBS = [
    "debug", "investigate", "diagnose", "troubleshoot", "trace",
    "find the bug", "find the error", "find the issue",
    "why is this", "what\'s wrong", "what is wrong",
]

# Explain verbs (when target is a file or code)
_EXPLAIN_VERBS = [
    "explain this", "explain the", "walk me through",
    "how does this work", "what does this do",
    "analyze this", "review this", "read this",
]


def detect_intent(task: str) -> str:
    """Classify task intent: qa, create, modify, debug, or explain.

    Returns one of: 'qa', 'create', 'modify', 'debug', 'explain'
    """
    t = task.lower().strip()

    # Q&A: starts with a question pattern AND has no action verbs
    all_action = _ACTION_VERBS + _MODIFY_VERBS
    if any(t.startswith(pat) for pat in _QA_STARTERS):
        if not any(re.search(r"\b" + re.escape(av) + r"\b", t) for av in all_action):
            return "qa"

    if t.endswith("?") and not any(re.search(r"\b" + re.escape(av) + r"\b", t) for av in all_action):
        return "qa"

    # Check if task starts with a create verb ("build a...", "create a...", "write a...")
    if any(t.startswith(cv) for cv in ["build", "create", "write", "make", "implement", "develop", "generate", "code", "design"]):
        return "create"

    # Debug: explicitly asking to debug/investigate
    if any(re.search(r"\b" + re.escape(dv) + r"\b", t) for dv in _DEBUG_VERBS):
        return "debug"

    # Explain: asking to explain existing code
    if any(re.search(r"\b" + re.escape(ev) + r"\b", t) for ev in _EXPLAIN_VERBS):
        return "explain"

    # Modify: acting on existing code (e.g. "refactor", "fix", "update")
    if any(re.search(r"\b" + re.escape(mv) + r"\b", t) for mv in ["refactor", "migrate", "fix", "update", "modify", "change", "delete", "remove", "rename"]):
        return "modify"

    # Create: building something new
    if any(re.search(r"\b" + re.escape(av) + r"\b", t) for av in _ACTION_VERBS):
        return "create"

    if any(re.search(r"\b" + re.escape(mv) + r"\b", t) for mv in _MODIFY_VERBS):
        return "modify"

    if t.endswith("?"):
        return "qa"

    return "create"


# -- Environment Detection -------------------------------------------------

def detect_environment() -> dict:
    """Detect OS, shell, Python version, and runtime environment.

    Returns dict with: os_name, shell, python_cmd, python_version
    """
    os_name = platform.system().lower()
    if os_name == "linux":
        # Check if we are inside WSL
        try:
            with open("/proc/version", "r") as f:
                version_info = f.read().lower()
            if "microsoft" in version_info or "wsl" in version_info:
                os_name = "wsl"
        except (FileNotFoundError, PermissionError):
            pass

    # Shell detection
    shell = _detect_shell(os_name)

    # Python command
    python_cmd = "python" if os_name == "windows" else "python3"

    # Python version
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    return {
        "os_name": os_name if os_name != "wsl" else "linux",
        "shell": "wsl" if os_name == "wsl" else shell,
        "python_cmd": python_cmd,
        "python_version": python_version,
    }


def _detect_shell(os_name: str) -> str:
    """Detect available shell, aligned with tools.py execution path."""

    if os_name == "windows":
        # Check if bash binary exists (Git Bash / MSYS)
        if shutil.which("bash"):
            return "bash"
        if _is_wsl_available():
            return "wsl"
        # Fallback to PowerShell
        if shutil.which("powershell") or shutil.which("pwsh"):
            return "powershell"
        return "cmd" 

    if os_name in ("linux", "wsl"):
        return "bash"  # Standard on Linux/WSL

    if os_name == "darwin":
        return "bash"  # Our commands work on both bash and zsh

    return "sh"


def _is_wsl_available() -> bool:
    """Check if WSL is installed and has at least one working distro."""
    try:
        result = subprocess.run(
            ["wsl", "--list", "--quiet"],
            capture_output=True, text=True, timeout=3,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


# -- Repository Scanner ----------------------------------------------------

def scan_repository(workdir: Path) -> dict:
    """Quick scan of repository to detect project type, frameworks, etc.

    Designed to run in under 30ms by checking only key indicator files.
    """
    workdir = workdir.resolve()

    has_git = (workdir / ".git").is_dir()
    has_venv = (workdir / ".venv").is_dir() or (workdir / "venv").is_dir()

    # Quick file count (capped scan)
    file_count = _quick_file_count(workdir, max_files=500)

    # Detect project type and frameworks by checking indicator files
    project_type, frameworks = _detect_project(workdir)

    # Find entry points
    entry_points = _find_entry_points(workdir, project_type)

    # Check for tests
    has_tests = _has_test_files(workdir)

    # Read key dependencies (fast -- just reads manifest files)
    dependencies = _read_dependencies(workdir, project_type)

    return {
        "has_git": has_git,
        "has_venv": has_venv,
        "file_count": file_count,
        "project_type": project_type,
        "frameworks": frameworks,
        "entry_points": entry_points,
        "has_tests": has_tests,
        "dependencies": dependencies,
    }


def _quick_file_count(workdir: Path, max_files: int = 500) -> int:
    """Count tracked files quickly, respecting .gitignore if possible."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=workdir, capture_output=True, text=True, timeout=3,
        )
        if result.returncode == 0 and result.stdout.strip():
            return len(result.stdout.strip().splitlines())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Fallback: walk directory
    count = 0
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv",
                 ".tox", "dist", "build", ".eggs", ".mypy_cache"}
    for root, dirs, files in os.walk(workdir):
        dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
        count += len(files)
        if count >= max_files:
            return count
    return count


def _detect_project(workdir: Path) -> Tuple[str, List[str]]:
    """Detect project type and frameworks from indicator files."""
    frameworks = []

    # Python indicators
    has_pyproject = (workdir / "pyproject.toml").exists()
    has_setup_py = (workdir / "setup.py").exists()
    has_requirements = (workdir / "requirements.txt").exists()
    has_pipfile = (workdir / "Pipfile").exists()

    if has_pyproject or has_setup_py or has_requirements or has_pipfile:
        frameworks = _detect_python_frameworks(workdir)
        return "python", frameworks

    # Node.js indicators
    if (workdir / "package.json").exists():
        frameworks = _detect_node_frameworks(workdir)
        return "node", frameworks

    # Rust
    if (workdir / "Cargo.toml").exists():
        return "rust", []

    # Go
    if (workdir / "go.mod").exists():
        return "go", []

    # Java
    if (workdir / "pom.xml").exists() or (workdir / "build.gradle").exists():
        return "java", []

    # Check if there are any source files at all
    for ext in (".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".cpp"):
        for _ in workdir.glob(f"*{ext}"):
            return "unknown", []

    return "empty", []


def _detect_python_frameworks(workdir: Path) -> List[str]:
    """Detect Python frameworks from requirements/pyproject."""
    frameworks = []
    content = ""

    for manifest in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]:
        path = workdir / manifest
        if path.exists():
            try:
                content += path.read_text(errors="replace").lower()
            except Exception:
                pass

    framework_map = {
        "fastapi": "fastapi",
        "flask": "flask",
        "django": "django",
        "pytest": "pytest",
        "sqlalchemy": "sqlalchemy",
        "pydantic": "pydantic",
        "celery": "celery",
        "redis": "redis",
        "pymongo": "mongodb",
        "torch": "pytorch",
        "tensorflow": "tensorflow",
        "numpy": "numpy",
        "pandas": "pandas",
        "streamlit": "streamlit",
        "gradio": "gradio",
    }

    for pkg, name in framework_map.items():
        if pkg in content:
            frameworks.append(name)

    return frameworks


def _detect_node_frameworks(workdir: Path) -> List[str]:
    """Detect Node.js frameworks from package.json."""
    frameworks = []
    pkg_path = workdir / "package.json"
    try:
        data = json.loads(pkg_path.read_text(errors="replace"))
        all_deps = {}
        all_deps.update(data.get("dependencies", {}))
        all_deps.update(data.get("devDependencies", {}))

        framework_map = {
            "react": "react", "next": "nextjs", "vue": "vue",
            "angular": "angular", "express": "express",
            "fastify": "fastify", "nest": "nestjs",
            "jest": "jest", "mocha": "mocha",
            "typescript": "typescript",
        }
        for pkg, name in framework_map.items():
            if any(pkg in dep for dep in all_deps):
                frameworks.append(name)
    except Exception:
        pass
    return frameworks


def _find_entry_points(workdir: Path, project_type: str) -> List[str]:
    """Find likely entry point files."""
    entry_names = [
        "main.py", "app.py", "server.py", "manage.py", "run.py",
        "index.py", "cli.py", "__main__.py",
        "index.js", "index.ts", "app.js", "app.ts", "server.js", "server.ts",
        "main.go", "main.rs", "Main.java",
    ]
    found = []
    for name in entry_names:
        if (workdir / name).exists():
            found.append(name)
        # Also check src/ directory
        if (workdir / "src" / name).exists():
            found.append(f"src/{name}")
    return found[:5]


def _has_test_files(workdir: Path) -> bool:
    """Check if the project has test files."""
    test_indicators = ["tests", "test", "__tests__", "spec"]
    for d in test_indicators:
        if (workdir / d).is_dir():
            return True

    # Check for test_*.py or *_test.py files in root
    try:
        for f in workdir.iterdir():
            if f.is_file() and (f.name.startswith("test_") or f.name.endswith("_test.py")):
                return True
    except PermissionError:
        pass
    return False


def _read_dependencies(workdir: Path, project_type: str) -> List[str]:
    """Read top-level dependency names (fast, no resolution)."""
    deps = []
    if project_type == "python":
        req_path = workdir / "requirements.txt"
        if req_path.exists():
            try:
                for line in req_path.read_text(errors="replace").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and not line.startswith("-"):
                        name = re.split(r"[=<>!~;\[]", line)[0].strip()
                        if name:
                            deps.append(name)
            except Exception:
                pass
    return deps[:20]


# -- Complexity Engine ------------------------------------------------------

def compute_complexity(intent: str, repo_info: dict, task: str) -> str:
    """Compute task complexity from intent + repo state + task text.

    This is smarter than pure keyword matching because it considers
    the actual project context.

    Returns: 'qa', 'low', 'medium', or 'high'
    """
    if intent == "qa":
        return "qa"

    task_lower = task.lower()
    file_count = repo_info.get("file_count", 0)
    frameworks = repo_info.get("frameworks", [])
    project_type = repo_info.get("project_type", "empty")

    # -- HIGH: explicitly complex multi-component tasks --
    high_keywords = [
        "full stack", "fullstack", "full-stack",
        "microservice", "e-commerce", "ecommerce",
        "docker", "kubernetes", "ci/cd", "pipeline",
        "machine learning", "deep learning", "neural network",
        "train a model", "training pipeline",
        "authentication", "oauth", "jwt auth",
        "database migration", "schema migration",
    ]
    if any(kw in task_lower for kw in high_keywords):
        return "high"

    # Large codebase + modify/debug -> high
    if intent in ("modify", "debug") and file_count > 50:
        if any(kw in task_lower for kw in ["refactor", "restructure", "redesign", "rewrite", "migrate"]):
            return "high"

    # -- MEDIUM: multi-step tasks --
    medium_keywords = [
        "api", "rest api", "graphql", "server", "backend", "frontend",
        "game", "snake", "tetris", "chess", "pong", "sudoku", "flappy", "arcade",
        "website", "web page", "web app", "webapp", "html", "css", "javascript",
        "test suite", "unit tests", "integration test", "e2e test",
        "dashboard", "portfolio", "application", "app with", "notes app", "todo app",
        "react", "vue", "angular", "next.js", "tailwind",
        "django", "flask app", "fastapi app", "express",
        "refactor", "migrate", "redesign", "restructure", "investigate",
    ]
    if any(kw in task_lower for kw in medium_keywords):
        return "medium"

    # Modify/debug on existing project with frameworks -> medium
    if intent in ("modify", "debug") and frameworks:
        return "medium"

    # Modify/debug on project with 10+ files -> medium
    if intent in ("modify", "debug") and file_count > 10:
        return "medium"

    # Create on existing project (adding to it) -> medium
    if intent == "create" and project_type not in ("empty", "unknown") and file_count > 5:
        return "medium"

    # -- LOW: everything else --
    return "low"


# -- Complexity Configuration -----------------------------------------------

COMPLEXITY_CONFIG = {
    "qa": {
        "max_tokens": 4096,
        "tool_set": "none",
        "enable_thinking": False,
    },
    "low": {
        "max_tokens": 8192,
        "tool_set": "core",
        "enable_thinking": False,
    },
    "medium": {
        "max_tokens": 16384,
        "tool_set": "full",
        "enable_thinking": True,
    },
    "high": {
        "max_tokens": 16384,
        "tool_set": "full",
        "enable_thinking": True,
    },
}


# -- Main Entry Point -------------------------------------------------------

def build_task_context(task: str, workdir: Path) -> TaskContext:
    """Build complete TaskContext by running all discovery phases.

    This is the single entry point -- call this from the orchestrator.
    Runs in under 50ms total, no LLM calls, no network.
    """
    # Phase 1: Intent
    intent = detect_intent(task)

    # Phase 2: Environment
    env = detect_environment()

    # Phase 3: Repository scan
    repo = scan_repository(workdir)

    # Phase 4: Complexity (uses intent + repo)
    complexity = compute_complexity(intent, repo, task)

    # Phase 5: Budget from complexity
    budget = COMPLEXITY_CONFIG[complexity]

    return TaskContext(
        # Intent
        intent=intent,
        complexity=complexity,
        # Environment
        os_name=env["os_name"],
        shell=env["shell"],
        python_cmd=env["python_cmd"],
        python_version=env["python_version"],
        has_venv=repo["has_venv"],
        has_git=repo["has_git"],
        # Repository
        project_type=repo["project_type"],
        frameworks=repo["frameworks"],
        file_count=repo["file_count"],
        has_tests=repo["has_tests"],
        entry_points=repo["entry_points"],
        dependencies=repo["dependencies"],
        # Budget
        max_tokens=budget["max_tokens"],
        tool_set=budget["tool_set"],
        enable_thinking=budget["enable_thinking"],
    )
