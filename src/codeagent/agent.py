import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", module="jupyter_client.*")

"""
CLI agent wrapper and presentation adapter for AlpieCode.

Delegates agent orchestration to AgentOrchestrator and handles Rich terminal UI output.
"""

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import Config, is_server_reachable
from .context import ContextManager, _serialize_assistant_message
from .executor import READ_ONLY_TOOLS, ToolExecutor, parse_text_tool_calls as _parse_text_tool_calls
from .backends.local_backend import LocalBackend
from .orchestrator import AgentEvent, AgentOrchestrator, resolve_backend
from .prompt import (
    OFFLINE_SYSTEM_PROMPT,
    OFFLINE_TOOLS,
    SYSTEM_PROMPT,
    PromptBuilder,
    is_simple_task as _is_simple_task,
)
from .session import SessionManager

# Re-export for backward compatibility
_build_system_prompt = lambda workdir, is_offline=False: PromptBuilder().build_system_prompt(workdir, is_offline)


# ── Rich console setup ────────────────────────────────────────────────

try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.markup import escape
    from rich.panel import Panel
    from rich.rule import Rule
    from rich.text import Text

    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

    def escape(text: str) -> str:
        return text

    class _FallbackConsole:
        def print(self, *args, **kwargs):
            kwargs.pop("style", None)
            kwargs.pop("highlight", None)
            print(*args, **kwargs)

        def rule(self, title="", **kwargs):
            print(f"\n{'─' * 20} {title} {'─' * 20}")

    console = _FallbackConsole()


def _print_reasoning(reasoning: str):
    if not reasoning or not reasoning.strip():
        return
    clean = reasoning.strip()
    if HAS_RICH:
        console.print(Text(f"💭 {clean}", style="dim italic"))
    else:
        console.print(f"💭 {clean}")


def _format_tool_summary(name: str, args: dict) -> str:
    if not isinstance(args, dict):
        return ""
    if name == "bash":
        cmd = args.get("command", "").strip()
        return f"$ {cmd[:80]}..." if len(cmd) > 80 else f"$ {cmd}"
    elif name in ("write_file", "edit_file", "read_file"):
        path = args.get("path", "")
        extra = ""
        if name == "write_file" and "content" in args:
            lines = len(str(args["content"]).splitlines())
            extra = f" ({lines} lines)"
        return f"{path}{extra}"
    elif name == "list_files":
        return args.get("path", ".")
    elif name in ("search", "web_search"):
        return f"'{args.get('query', '')}'"
    elif name == "fetch_web_page":
        return args.get("url", "")
    else:
        parts = [f"{k}={repr(v)[:30]}" for k, v in args.items() if k != "content"]
        return " ".join(parts)


def _print_tool_call(turn: int, name: str, args: dict):
    summary = _format_tool_summary(name, args)
    if HAS_RICH:
        console.print(f"\n⏺ [bold cyan]{name}[/bold cyan] [white]{summary}[/white]")
    else:
        console.print(f"\n⏺ {name} {summary}")


def _print_tool_result(result: str):
    clean = result.strip()
    if '"exit_code"' in clean:
        try:
            data = json.loads(clean.split("\n", 1)[-1] if clean.startswith("⚠️") else clean)
            out = data.get("stdout", "").strip()
            err = data.get("stderr", "").strip()
            code = data.get("exit_code", 0)
            if code == 0:
                clean = out if out else "success"
            else:
                clean = f"exit {code}: {err}" if err else f"exit {code}"
        except Exception:
            pass

    lines = clean.splitlines()
    if len(lines) > 8:
        display = "\n".join(lines[:6]) + f"\n  ... ({len(lines)-6} lines omitted)"
    else:
        display = clean[:500] + ("..." if len(clean) > 500 else "")

    if HAS_RICH:
        style = "dim green" if not ("exit 1" in clean or "error:" in clean.lower()[:30]) else "dim red"
        console.print(Text(f"  └ {display}", style=style))
    else:
        console.print(f"  └ {display}")


def _print_assistant_message(content: str):
    if not content or not content.strip():
        return
    text = content.strip()
    if text.upper().startswith("DONE:"):
        text = text[5:].strip()
    if HAS_RICH:
        try:
            console.print()
            console.print(Markdown(text))
        except Exception:
            console.print()
            console.print(text)
    else:
        print(f"\n{text}")


# ── Git helpers ───────────────────────────────────────────────────────

def _is_safe_git_dir(workdir: Path) -> bool:
    try:
        home = Path.home().resolve()
        wd = workdir.resolve()
        if wd == home or wd == Path("/") or wd == Path("C:\\"):
            return False
        try:
            items = list(wd.iterdir())
            if len(items) > 500:
                return False
        except PermissionError:
            return False
    except Exception:
        return False
    return True


def _ensure_git(workdir: Path) -> None:
    if not _is_safe_git_dir(workdir):
        return
    if not (workdir / ".git").exists():
        try:
            subprocess.run(["git", "init"], cwd=workdir, capture_output=True, timeout=10)
            subprocess.run(["git", "add", "-A"], cwd=workdir, capture_output=True, timeout=30)
            subprocess.run(["git", "commit", "-m", "initial commit", "--allow-empty"], cwd=workdir, capture_output=True, timeout=10)
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass


def _checkpoint(workdir: Path, message: str) -> None:
    if not (workdir / ".git").exists():
        return
    try:
        subprocess.run(["git", "add", "-A"], cwd=workdir, capture_output=True, timeout=30)
        subprocess.run(["git", "commit", "-m", message, "--allow-empty"], cwd=workdir, capture_output=True, timeout=10)
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass


# ── Main CLI Agent Functions ──────────────────────────────────────────

def run_agent(
    task: str,
    workdir: Path,
    cfg: Config,
    verbose: bool = True,
    image_path: str = None,
    video_path: str = None,
    url: str = None,
    github_repo: str = None,
    server_url: str = None,
    complexity: str = None,
    debug: bool = False,
) -> list:
    """Run non-interactive agent task with Rich presentation."""
    workdir = workdir.resolve()
    _ensure_git(workdir)

    # CLI-as-Client check: auto-detect if local/remote server is running
    from .client import AlpieCodeClient
    target_server = server_url or getattr(cfg, "server_url", None)
    if not target_server:
        # Check default local server
        local_client = AlpieCodeClient("http://127.0.0.1:7169")
        if local_client.health().get("status") == "online":
            target_server = "http://127.0.0.1:7169"

    if target_server:
        client = AlpieCodeClient(target_server)
        event_stream = client.stream_chat(
            task=task,
            workdir=str(workdir),
            image_path=image_path,
            video_path=video_path,
            url=url,
            github_repo=github_repo,
            complexity=complexity,
        )
    else:
        backend = resolve_backend(cfg)
        orchestrator = AgentOrchestrator(backend)
        session_mgr = SessionManager()
        session = session_mgr.create_session(workdir, max_tokens=cfg.n_ctx if not backend.is_available else 262_144)
        event_stream = orchestrator.run_task(
            session=session,
            task=task,
            cfg=cfg,
            image_path=image_path,
            video_path=video_path,
            url=url,
            github_repo=github_repo,
            complexity=complexity,
        )

    _checkpoint(workdir, "checkpoint: start")

    current_turn = 0
    last_discovery = {}

    for event in event_stream:
        if event.type == "discovery" and verbose:
            last_discovery = event.data
            if debug and HAS_RICH:
                console.print(Panel(
                    f"[bold cyan]🔍 Autonomous Discovery Engine[/bold cyan]\n"
                    f"• Intent: [bold]{event.data.get('intent')}[/bold]\n"
                    f"• Complexity: [bold]{event.data.get('complexity')}[/bold]\n"
                    f"• OS: {event.data.get('os')} | Shell: {event.data.get('shell')}\n"
                    f"• Project: {event.data.get('project_type')} ({event.data.get('file_count', 0)} files)\n"
                    f"• Frameworks: {', '.join(event.data.get('frameworks', [])) or 'None'}",
                    title="Pre-Execution Intelligence",
                    border_style="dim cyan",
                    padding=(0, 1)
                ))
            elif debug:
                print(f"[Discovery] intent={event.data.get('intent')}, complexity={event.data.get('complexity')}, shell={event.data.get('shell')}, project={event.data.get('project_type')}")

        elif event.type == "start" and verbose:
            data = event.data
            if debug:
                if HAS_RICH:
                    console.rule("[bold blue]Agent Started (Debug)[/bold blue]")
                    console.print(Text(f"📋 Task: {task.splitlines()[0]}", style="bold"))
                    console.print(f"📂 Workdir: {workdir}", style="dim")
                    mode_str = "[bold green]ONLINE[/bold green]" if not data["is_offline"] else "[bold yellow]OFFLINE[/bold yellow]"
                    console.print(f"🌐 Mode: {mode_str}", style="dim")
                    comp = data.get("complexity", "low")
                    comp_label = {"qa": "Q&A (instant)", "low": "Low (fast)", "medium": "Medium (balanced)", "high": "High (thorough)"}.get(comp, comp)
                    console.print(f"⚡ Complexity: {comp_label}", style="dim")
                    if last_discovery:
                        console.print(f"🔍 Discovery: {last_discovery.get('intent', 'create')} on {last_discovery.get('project_type', 'empty')} project", style="dim")
                else:
                    print(f"[Start] task={task.splitlines()[0]}, mode={'offline' if data['is_offline'] else 'online'}")
            else:
                # Clean, professional presentation like Claude Code / Codex
                if data.get("is_offline"):
                    if HAS_RICH:
                        console.print("[dim yellow]⚡ Offline mode[/dim yellow]")
                    else:
                        print("⚡ Offline mode")
                if github_repo:
                    console.print(f"🐙 GitHub Repo: {github_repo}", style="cyan")
                if image_path:
                    console.print(f"🖼️  Image: {image_path}", style="cyan")
                if video_path:
                    console.print(f"🎬 Video: {video_path}", style="cyan")
                if url:
                    console.print(f"📺 URL: {url}", style="cyan")

        elif event.type == "adaptive_mode" and verbose and HAS_RICH:
            console.print("⚡ [dim]Adaptive mode: simple task detected, skipping deep reasoning for speed[/dim]")

        elif event.type == "turn_start":
            current_turn = event.data["turn"]
            if debug:
                if HAS_RICH:
                    console.print(f"[dim]── Step {current_turn} ──[/dim]")
                else:
                    print(f"── Step {current_turn} ──")

        elif event.type == "compaction" and verbose:
            console.print("🗜️  Compacting context (approaching token limit)...", style="yellow")

        elif event.type == "wrap_up" and verbose:
            if HAS_RICH:
                console.print(f"⏳ [bold yellow]Wrap-up: {event.data['remaining']} turns remaining[/bold yellow]", style="yellow")

        elif event.type == "thinking" and verbose:
            _print_reasoning(event.data["content"])

        elif event.type == "tool_call" and verbose:
            _print_tool_call(event.data["turn"], event.data["name"], event.data["arguments"])

        elif event.type == "tool_result":
            if verbose:
                _print_tool_result(event.data["content"])
            _checkpoint(workdir, f"checkpoint: turn {event.data['turn']}")

        elif event.type == "message" and verbose:
            _print_assistant_message(event.data["content"])
            _checkpoint(workdir, "checkpoint: response")

        elif event.type == "fallback" and verbose:
            err_str = escape(str(event.data.get('error', '')))
            if HAS_RICH:
                console.print(f"\n⚠️  [bold yellow]Online Server Error / Timeout[/bold yellow] ({err_str})", style="yellow")
                console.print("🔄 [bold cyan]Auto-falling back to local GGUF engine...[/bold cyan]", style="cyan")
            else:
                print(f"\n⚠️ Online Server Error: {event.data['error']}")
                print("🔄 Auto-falling back to local GGUF engine...")

        elif event.type == "error" and verbose:
            if HAS_RICH:
                console.print(Text(f"\n❌ Model Error\n   Error: {event.data['error']}\n", style="bold red"))
            else:
                print(f"\n❌ Model Error: {event.data['error']}")

        elif event.type == "stall_intervention" and verbose:
            if HAS_RICH:
                console.print(
                    f"🔄 [bold yellow]Progress stall detected[/bold yellow] "
                    f"(turn {event.data['turn']}, {event.data['consecutive_stalls']} stalled turns, "
                    f"intervention #{event.data['interventions']})",
                    style="yellow"
                )
            else:
                print(f"🔄 Progress stall detected (turn {event.data['turn']})")

        elif event.type == "turn_progress" and debug:
            snap = event.data
            status = "✅" if snap["had_progress"] else "⚠️"
            if HAS_RICH:
                console.print(
                    Text(f"  {status} Progress: created={snap['files_created']}, "
                    f"modified={snap['files_modified']}, stalls={snap['consecutive_stalls']}"),
                    style="dim"
                )

        elif event.type == "safety_ceiling" and verbose:
            if HAS_RICH:
                console.print(
                    f"\n🛑 [bold red]Safety ceiling ({event.data['ceiling']} turns) reached.[/bold red]\n"
                    "This is an emergency stop — the agent may be stuck in an unrecoverable loop.",
                    style="bold red"
                )
            else:
                print(f"\n🛑 Safety ceiling ({event.data['ceiling']}) reached.")

        elif event.type == "done":
            summary = event.data.get("summary", "")
            _checkpoint(workdir, "checkpoint: done")
            if debug and HAS_RICH:
                console.rule("[bold green]✅ Complete[/bold green]")

        elif event.type == "max_turns_reached" and verbose:
            progress = event.data.get("progress", {})
            if HAS_RICH:
                console.print(f"\n⚠️  [bold yellow]Safety ceiling ({event.data['max_turns']}) reached.[/bold yellow]", style="bold yellow")
                if progress:
                    console.print(
                        f"   Progress: {progress.get('progress_turns', 0)}/{progress.get('total_turns', 0)} turns made progress, "
                        f"{progress.get('files_created', 0)} files created, "
                        f"{progress.get('stall_interventions', 0)} stall interventions",
                        style="dim"
                    )
            else:
                print(f"\n⚠️ Safety ceiling ({event.data['max_turns']}) reached.")

    return session.context.messages if "session" in locals() else []


def run_chat(workdir: Path, cfg: Config, verbose: bool = True) -> None:
    """Run interactive chat session with Rich presentation."""
    workdir = workdir.resolve()
    _ensure_git(workdir)

    backend = resolve_backend(cfg)
    orchestrator = AgentOrchestrator(backend)
    session_mgr = SessionManager()
    session = session_mgr.create_session(workdir, max_tokens=cfg.n_ctx if not backend.is_available else 262_144)

    is_offline = isinstance(backend, LocalBackend) or not backend.is_available
    active_tools = PromptBuilder().get_tools(is_offline=is_offline)

    if HAS_RICH:
        console.print()
        mode_line = "🌐 Mode: [bold green]ONLINE[/bold green]\n🤖 Model: [bold cyan]alpie_9b[/bold cyan]" if not is_offline else "🧠 Mode: [bold yellow]OFFLINE[/bold yellow]\n🤖 Model: [bold cyan]alpie_9b (Local GGUF)[/bold cyan]"
        console.print(
            Panel(
                f"[bold cyan]AlpieCode[/bold cyan] interactive mode\n"
                f"📂 Working in: [cyan]{workdir}[/cyan]\n"
                f"{mode_line}\n\n"
                "Type your request, or [bold red]exit[/bold red] / [bold red]quit[/bold red] to stop.",
                title="💬 Chat Mode",
                border_style="blue",
            )
        )
    else:
        console.print("\n💬 Chat Mode — type your request, or 'exit' to stop.")
        console.print(f"📂 Working in: {workdir}")

    while True:
        try:
            if HAS_RICH:
                user_input = console.input("\n[bold green]You ❯[/bold green] ").strip()
            else:
                user_input = input("\nYou ❯ ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye! 👋")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            console.print("Goodbye! 👋")
            break

        for event in orchestrator.run_task(session, user_input, cfg):
            if event.type == "turn_start" and debug:
                if HAS_RICH:
                    console.print(f"[dim]── Step {event.data['turn']} ──[/dim]")
                else:
                    print(f"── Step {event.data['turn']} ──")

            elif event.type == "thinking" and verbose:
                _print_reasoning(event.data["content"])

            elif event.type == "tool_call" and verbose:
                _print_tool_call(event.data["turn"], event.data["name"], event.data["arguments"])

            elif event.type == "tool_result":
                if verbose:
                    _print_tool_result(event.data["content"])
                _checkpoint(workdir, f"checkpoint: chat turn {event.data['turn']}")

            elif event.type == "message":
                _print_assistant_message(event.data["content"])
                _checkpoint(workdir, "checkpoint: done")

            elif event.type == "error":
                if HAS_RICH:
                    console.print(Text(f"❌ Model error: {event.data['error']}", style="bold red"))
                else:
                    print(f"❌ Model error: {event.data['error']}")

            elif event.type == "done":
                break
