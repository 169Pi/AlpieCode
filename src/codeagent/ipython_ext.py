"""
IPython & Jupyter / Google Colab extension for AlpieCode.

Enables seamless usage of AlpieCode inside Jupyter Notebooks, JupyterLab,
and Google Colab via cell/line magic commands and rich interactive displays:

    %load_ext alpiecode
    %alpie write a quick pandas script to inspect data.csv
    %%alpie
    Create a complete PyTorch model training pipeline.
"""

import html
import re
import sys
import warnings
from pathlib import Path
from typing import Optional, List, Dict, Any

# Suppress noisy Jupyter / Python 3.12+ deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", module="jupyter_client.*")
warnings.filterwarnings("ignore", module="ipykernel.*")

from .config import load_config
from .orchestrator import AgentOrchestrator, AgentEvent, resolve_backend
from .session import SessionManager
from .agent import run_agent


def _is_notebook() -> bool:
    """Check if code is running inside a web browser notebook (Jupyter, Colab, VS Code Notebook)."""
    try:
        from IPython import get_ipython
        shell = get_ipython()
        if shell is None:
            return False
        shell_name = shell.__class__.__name__
        if "TerminalInteractiveShell" in shell_name:
            return False
        if "ZMQInteractiveShell" in shell_name or hasattr(shell, "kernel") or "google.colab" in sys.modules:
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


def _get_notebook_context() -> str:
    """Inspect active user variables in the notebook session (DataFrames, tensors, etc.)."""
    try:
        from IPython import get_ipython
        ip = get_ipython()
        if not ip or not hasattr(ip, "user_ns"):
            return ""

        var_summaries = []
        for name, val in list(ip.user_ns.items()):
            if name.startswith("_"):
                continue
            type_name = type(val).__name__
            module_name = getattr(type(val), "__module__", "")

            # Pandas DataFrame
            if "pandas" in module_name and type_name == "DataFrame":
                cols = list(val.columns)[:15]
                var_summaries.append(f"- DataFrame `{name}`: shape={val.shape}, columns={cols}")
            # Pandas Series
            elif "pandas" in module_name and type_name == "Series":
                var_summaries.append(f"- Series `{name}`: shape={val.shape}, dtype={val.dtype}")
            # Numpy ndarray
            elif "numpy" in module_name and type_name == "ndarray":
                var_summaries.append(f"- NumPy Array `{name}`: shape={val.shape}, dtype={val.dtype}")
            # PyTorch Tensor
            elif "torch" in module_name and "Tensor" in type_name:
                shape = list(val.shape) if hasattr(val, "shape") else []
                var_summaries.append(f"- PyTorch Tensor `{name}`: shape={shape}, dtype={getattr(val, 'dtype', 'unknown')}")

        if not var_summaries:
            return ""
        return "\n[Active In-Memory Notebook Variables]\n" + "\n".join(var_summaries[:8]) + "\n"
    except Exception:
        return ""


def _extract_primary_code_block(text: str) -> Optional[str]:
    """Extract Python code block from assistant text to insert into cell."""
    # Match ```python ... ``` or ```py ... ```
    match = re.search(r"```(?:python|py)\n(.*?)```", text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    # Match generic ``` ... ```
    match = re.search(r"```\n(.*?)```", text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _render_colab_card(task: str, tool_actions: List[Dict[str, str]], content: str) -> str:
    """Render a modern, sleek Colab/Jupyter responsive card."""
    task_escaped = html.escape(task[:140])
    
    actions_html = ""
    if tool_actions:
        actions_html = '<div style="margin-top: 8px; margin-bottom: 8px; font-family: ui-monospace, monospace; font-size: 12px;">'
        for act in tool_actions:
            name = html.escape(act.get("name", ""))
            summary = html.escape(act.get("summary", ""))
            status = act.get("status", "✓")
            actions_html += (
                f'<div style="display: flex; align-items: center; gap: 6px; padding: 3px 0; color: #94a3b8;">'
                f'<span style="color: #38bdf8;">⏺</span> '
                f'<strong style="color: #f1f5f9;">{name}</strong> '
                f'<span style="color: #64748b;">{summary}</span>'
                f'</div>'
            )
        actions_html += '</div>'

    card = (
        f'<div style="'
        f'background: #0f172a; border: 1px solid #1e293b; border-left: 4px solid #38bdf8; '
        f'border-radius: 8px; padding: 12px 16px; margin: 8px 0; font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif;'
        f'box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);">'
        f'<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e293b; padding-bottom: 8px;">'
        f'<span style="font-weight: 600; font-size: 13px; color: #38bdf8; display: flex; align-items: center; gap: 6px;">'
        f'⚡ AlpieCode Agent'
        f'</span>'
        f'<span style="font-size: 11px; color: #64748b; background: #1e293b; padding: 2px 8px; border-radius: 9999px;">'
        f'Goal-Driven'
        f'</span>'
        f'</div>'
        f'<div style="font-size: 13px; color: #cbd5e1; margin-top: 8px; font-weight: 500;">{task_escaped}</div>'
        f'{actions_html}'
        f'</div>'
    )
    return card


def alpie_magic(line: str, cell: Optional[str] = None):
    """
    %alpie <task>        (line magic)
    %%alpie              (cell magic)
    <multiline task>

    Flags:
      --insert, -i: Automatically insert generated code into the next cell
    """
    raw_task = (cell if cell is not None and cell.strip() else line).strip()
    if not raw_task:
        print("Usage: %alpie <task>  OR  %%alpie\n<multiline task>")
        return

    # Check for --insert flag
    auto_insert = False
    if raw_task.startswith("--insert ") or raw_task.startswith("-i "):
        auto_insert = True
        raw_task = re.sub(r"^(--insert|-i)\s+", "", raw_task).strip()

    # Append in-memory notebook context (DataFrames, tensors)
    nb_context = _get_notebook_context()
    full_task = f"{raw_task}\n{nb_context}" if nb_context else raw_task

    cfg = load_config()
    workdir = Path(".").resolve()

    if not _is_notebook():
        # Running in standard terminal / ipython shell
        run_agent(full_task, workdir, cfg, verbose=True)
        return

    # In Jupyter or Google Colab: run with rich streaming & UI
    from IPython import get_ipython
    ip = get_ipython()

    backend = resolve_backend(cfg)
    orchestrator = AgentOrchestrator(backend)
    session_mgr = SessionManager()
    session = session_mgr.create_session(workdir, max_tokens=cfg.n_ctx if not backend.is_available else 262_144)

    tool_actions: List[Dict[str, str]] = []
    final_content = ""

    for event in orchestrator.run_task(session=session, task=full_task, cfg=cfg):
        if event.type == "tool_call":
            t_name = event.data.get("name", "")
            t_args = event.data.get("arguments", {})
            if isinstance(t_args, str):
                try:
                    import json
                    t_args = json.loads(t_args)
                except Exception:
                    t_args = {}
            
            summary = ""
            if t_name == "bash":
                cmd = t_args.get("command", "")
                summary = f"$ {cmd[:60]}..." if len(cmd) > 60 else f"$ {cmd}"
            elif t_name in ("write_file", "edit_file", "read_file"):
                summary = str(t_args.get("path", ""))
            tool_actions.append({"name": t_name, "summary": summary})

        elif event.type == "message":
            final_content = event.data.get("content", "")

        elif event.type == "done":
            if not final_content:
                final_content = event.data.get("summary", "")

    # Clean up DONE: prefix
    cleaned_content = final_content.strip()
    if cleaned_content.upper().startswith("DONE:"):
        cleaned_content = cleaned_content[5:].strip()

    # Render modern card & markdown
    _display_html(_render_colab_card(raw_task, tool_actions, cleaned_content))
    if cleaned_content:
        _display_markdown(cleaned_content)

    # If code block is present, insert into next cell if requested or suggested
    code_block = _extract_primary_code_block(cleaned_content)
    if code_block and (auto_insert or (cell is not None and "code" in raw_task.lower())):
        try:
            ip.set_next_input(code_block, replace=False)
            _display_html(
                '<div style="font-size: 11px; color: #10b981; margin-top: 4px; font-family: sans-serif;">'
                '✨ Code block automatically populated in next cell. Hit <b>Shift+Enter</b> to run.'
                '</div>'
            )
        except Exception:
            pass


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

    alpie_magic(plan_task)


def alpie_explain_magic(line: str):
    """%alpie_explain <file_path_or_concept> — Explain code or architecture."""
    target = line.strip()
    if not target:
        print("Usage: %alpie_explain <file_path_or_concept>")
        return

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

    alpie_magic(explain_task)


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
    if _is_notebook():
        _display_html(
            '<div style="background: #0f172a; border-left: 4px solid #38bdf8; border-radius: 6px; padding: 8px 12px; margin: 4px 0; font-family: sans-serif; font-size: 13px; color: #e2e8f0;">'
            '<strong style="color: #38bdf8;">✨ AlpieCode IPython & Colab Extension Loaded!</strong> '
            '<span style="color: #94a3b8; font-size: 12px;">Try: <code>%alpie &lt;task&gt;</code> or <code>%%alpie</code> (supports <code>--insert</code> to populate code cells)</span>'
            '</div>'
        )
    else:
        print("✨ AlpieCode IPython/Jupyter Extension Loaded! Try: %alpie <task> or %%alpie")


def unload_ipython_extension(ipython):
    """Called when user runs `%unload_ext alpiecode`."""
    pass
