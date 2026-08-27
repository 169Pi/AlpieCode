"""
IPython & Jupyter / Google Colab extension for AlpieCode.

Enables seamless usage of AlpieCode inside Jupyter Notebooks, JupyterLab,
and Google Colab via cell/line magic commands and rich interactive displays:

    %load_ext alpiecode
    %alpie write a quick pandas script to inspect data.csv
    %%alpie
    Create a complete PyTorch model training pipeline.
"""

import sys
import warnings
from pathlib import Path
from typing import Optional

# Suppress noisy Jupyter / Python 3.12+ deprecation warnings (e.g. datetime.utcnow in jupyter_client)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", module="jupyter_client.*")
warnings.filterwarnings("ignore", module="ipykernel.*")

from .config import load_config
from .agent import run_agent


def _is_notebook() -> bool:
    """Check if code is running inside a Jupyter notebook or Google Colab."""
    try:
        from IPython import get_ipython
        shell = get_ipython()
        if shell is None:
            return False
        shell_name = shell.__class__.__name__
        if "ZMQInteractiveShell" in shell_name or "Shell" in shell_name:
            return True
        return False
    except Exception:
        return False


def _display_html(html_str: str):
    """Render rich HTML in Jupyter or Google Colab."""
    try:
        from IPython.display import HTML, display
        display(HTML(html_str))
    except Exception:
        print(html_str)


def _display_markdown(md_str: str):
    """Render rich Markdown in Jupyter or Google Colab."""
    try:
        from IPython.display import Markdown, display
        display(Markdown(md_str))
    except Exception:
        print(md_str)


def alpie_magic(line: str, cell: Optional[str] = None):
    """
    %alpie <task>        (line magic)
    %%alpie              (cell magic)
    <multiline task>
    """
    task = (cell if cell is not None and cell.strip() else line).strip()
    if not task:
        print("Usage: %alpie <task>  OR  %%alpie\\n<multiline task>")
        return

    cfg = load_config()
    workdir = Path(".").resolve()

    if _is_notebook():
        _display_html(
            f'<div style="border-left: 3px solid #60a5fa; padding: 6px 12px; background: rgba(96,165,250,0.08); border-radius: 4px; font-family: sans-serif; margin-bottom: 8px;">'
            f'<strong style="color: #60a5fa;">⚡ AlpieCode Agent:</strong> {task[:120]}'
            f'</div>'
        )

    run_agent(task, workdir, cfg, verbose=True)


def alpie_plan_magic(line: str, cell: Optional[str] = None):
    """%alpie_plan <task> — Generate a structured implementation plan without making edits."""
    task = (cell if cell is not None and cell.strip() else line).strip()
    if not task:
        print("Usage: %alpie_plan <task>")
        return

    plan_task = (
        f"PLANNING ONLY — Do NOT make any file edits. "
        f"Analyze the codebase and create a detailed implementation plan for the following task. "
        f"Use list_files, read_file, and file_search to understand the project. "
        f"Then use update_plan to write a structured plan with deliverables and checks. "
        f"Finish with DONE: when the plan is complete.\n\n"
        f"Task: {task}"
    )

    cfg = load_config()
    workdir = Path(".").resolve()
    run_agent(plan_task, workdir, cfg, verbose=True)


def alpie_explain_magic(line: str):
    """%alpie_explain <file_path_or_concept> — Explain code or architecture."""
    target = line.strip()
    if not target:
        print("Usage: %alpie_explain <file_path_or_concept>")
        return

    cfg = load_config()
    workdir = Path(".").resolve()
    target_path = workdir / target if not Path(target).is_absolute() else Path(target)

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
        explain_task = (
            f"EXPLANATION ONLY — Do NOT make any file edits.\n\n"
            f"Explain the following codebase concept or architecture in detail:\n"
            f"Topic: {target}\n\n"
            f"Use read_file or file_search if needed to understand codebase context."
        )

    run_agent(explain_task, workdir, cfg, verbose=True)


def alpie_doctor_magic(line: str = ""):
    """%alpie_doctor — Run system health diagnostic checks."""
    from .doctor import run_doctor
    run_doctor()


def load_ipython_extension(ipython):
    """Called by IPython when user runs `%load_ext alpiecode`."""
    ipython.register_magic_function(alpie_magic, magic_kind="line_cell", magic_name="alpie")
    ipython.register_magic_function(alpie_plan_magic, magic_kind="line_cell", magic_name="alpie_plan")
    ipython.register_magic_function(alpie_explain_magic, magic_kind="line", magic_name="alpie_explain")
    ipython.register_magic_function(alpie_doctor_magic, magic_kind="line", magic_name="alpie_doctor")
    print("✨ AlpieCode IPython/Jupyter Extension Loaded! Try: %alpie <task> or %%alpie")


def unload_ipython_extension(ipython):
    """Called when user runs `%unload_ext alpiecode`."""
    pass
