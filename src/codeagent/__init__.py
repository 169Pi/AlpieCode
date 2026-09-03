import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", module="jupyter_client.*")

"""
AlpieCode — Autonomous AI Coding Agent powered by local 169Pi GGUF VLM & Online API.

Supports:
- CLI usage (`alpiecode run`, `alpiecode serve`, `alpiecode doctor`)
- Jupyter Notebooks & Google Colab (`%load_ext alpiecode`, `%alpie <task>`)
- Python SDK API (`import alpiecode; alpiecode.run("...")`)
- VS Code Extension
"""

from pathlib import Path
from typing import Optional, Any, Dict

__version__ = "7.0.1"


def run(task: str, workdir: str = ".", reasoning_level: str = "medium", **kwargs):
    """Run an autonomous coding task programmatically."""
    from .config import load_config
    from .agent import run_agent
    cfg = load_config()
    if reasoning_level == "low":
        cfg.enable_thinking = False
        cfg.temperature = 0.0
    elif reasoning_level == "medium":
        cfg.enable_thinking = True
        cfg.temperature = 0.1
    elif reasoning_level == "high":
        cfg.enable_thinking = True
        cfg.temperature = 0.2
    return run_agent(task, Path(workdir).resolve(), cfg, verbose=kwargs.get("verbose", True))


def plan(task: str, workdir: str = ".", **kwargs):
    """Generate an implementation plan without making edits."""
    from .config import load_config
    from .agent import run_agent
    cfg = load_config()
    plan_task = (
        f"PLANNING ONLY — Do NOT make any file edits. "
        f"Analyze the codebase and create a detailed implementation plan for the following task. "
        f"Use list_files, read_file, and file_search to understand the project. "
        f"Then use update_plan to write a structured plan with deliverables and checks. "
        f"Finish with DONE: when the plan is complete.\n\n"
        f"Task: {task}"
    )
    return run_agent(plan_task, Path(workdir).resolve(), cfg, verbose=kwargs.get("verbose", True))


def explain(target: str, workdir: str = ".", **kwargs):
    """Explain a file, function, or concept."""
    from .config import load_config
    from .agent import run_agent
    cfg = load_config()
    target_path = Path(workdir) / target if not Path(target).is_absolute() else Path(target)
    if target_path.exists() and target_path.is_file():
        content = target_path.read_text(encoding="utf-8", errors="replace")
        explain_task = (
            f"EXPLANATION ONLY — Do NOT make any file edits.\n\n"
            f"Please explain the file `{target}` in detail:\n"
            f"1. Overview of its purpose and role\n"
            f"2. Key functions, classes, and internal logic\n"
            f"3. Dependencies and how it connects to the project\n"
            f"4. Step-by-step walkthrough of how it executes\n\n"
            f"File content ({target}):\n```\n{content[:16000]}\n```"
        )
    else:
        explain_task = f"EXPLANATION ONLY — Do NOT make any file edits.\n\nExplain topic: {target}"
    return run_agent(explain_task, Path(workdir).resolve(), cfg, verbose=kwargs.get("verbose", True))


def chat(workdir: str = ".", **kwargs):
    """Start an interactive CLI chat session."""
    from .config import load_config
    from .agent import run_chat
    cfg = load_config()
    return run_chat(Path(workdir).resolve(), cfg, verbose=kwargs.get("verbose", True))


def doctor() -> int:
    """Run system health diagnostics."""
    from .doctor import run_doctor
    return run_doctor()


# Re-export IPython extension loaders so `%load_ext alpiecode` works seamlessly
def load_ipython_extension(ipython):
    from .ipython_ext import load_ipython_extension as _load
    _load(ipython)


def unload_ipython_extension(ipython):
    from .ipython_ext import unload_ipython_extension as _unload
    _unload(ipython)


__all__ = [
    "run",
    "plan",
    "explain",
    "chat",
    "doctor",
    "load_ipython_extension",
    "unload_ipython_extension",
    "__version__",
]
