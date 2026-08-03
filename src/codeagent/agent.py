"""
Core agent loop for codeagent.

Sends user tasks to the VLM endpoint, executes tool calls,
displays reasoning/thinking, and manages git checkpoints.
"""

import json
import subprocess
import sys
from pathlib import Path

import httpx
from openai import OpenAI

from .config import Config
from .tools import TOOLS, make_dispatch

SYSTEM_PROMPT = """\
You are a coding agent working inside a git repository at the current directory.
Use the available tools to inspect the repo, make edits, run commands/tests, and verify your work.

Guidelines:
- Start by listing files to understand the project structure
- Prefer minimal, targeted edits over full rewrites
- Always verify your changes with a test or command before finishing
- IMPORTANT: When the task is complete, you MUST respond with a short text message (not a tool call) that starts with the word DONE: followed by a brief summary. Keep your final answer concise.
"""

# ── Rich console setup ────────────────────────────────────────────────

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.markdown import Markdown
    from rich.text import Text
    from rich.rule import Rule

    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

    class _FallbackConsole:
        """Minimal console fallback when rich is not installed."""
        def print(self, *args, **kwargs):
            kwargs.pop("style", None)
            kwargs.pop("highlight", None)
            print(*args, **kwargs)
        def rule(self, title="", **kwargs):
            print(f"\n{'─' * 20} {title} {'─' * 20}")

    console = _FallbackConsole()


def _print_reasoning(reasoning: str):
    """Display the model's thinking/reasoning."""
    if not reasoning or not reasoning.strip():
        return
    if HAS_RICH:
        text = Text(reasoning.strip(), style="dim italic")
        console.print(Panel(text, title="💭 Thinking", border_style="dim blue", padding=(0, 1)))
    else:
        console.print(f"\n💭 Thinking: {reasoning.strip()}")


def _print_tool_call(turn: int, name: str, args: dict):
    """Display a tool invocation."""
    # Truncate long args for display
    display_args = {}
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 200:
            display_args[k] = v[:200] + "..."
        else:
            display_args[k] = v

    if HAS_RICH:
        args_str = json.dumps(display_args, indent=2)
        console.print(f"\n🔧 [bold cyan]Tool:[/bold cyan] [bold]{name}[/bold]", highlight=False)
        console.print(f"   {args_str}", style="cyan", highlight=False)
    else:
        console.print(f"\n🔧 Tool: {name}({display_args})")


def _print_tool_result(result: str):
    """Display a tool result (truncated)."""
    truncated = result[:1500] + ("..." if len(result) > 1500 else "")
    if HAS_RICH:
        console.print(f"   → {truncated}", style="green", highlight=False)
    else:
        console.print(f"   → {truncated}")


def _print_assistant_message(content: str):
    """Display the assistant's final text response."""
    if HAS_RICH:
        try:
            md = Markdown(content)
            console.print(Panel(md, title="🤖 Assistant", border_style="green", padding=(0, 1)))
        except Exception:
            console.print(Panel(content, title="🤖 Assistant", border_style="green", padding=(0, 1)))
    else:
        console.print(f"\n🤖 Assistant: {content}")


# ── Git helpers ───────────────────────────────────────────────────────

def _ensure_git(workdir: Path) -> None:
    """Initialize git repo if not already one."""
    if not (workdir / ".git").exists():
        subprocess.run(["git", "init"], cwd=workdir, capture_output=True)
        subprocess.run(["git", "add", "-A"], cwd=workdir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial commit", "--allow-empty"], cwd=workdir, capture_output=True)


def _checkpoint(workdir: Path, message: str) -> None:
    """Create a git checkpoint commit."""
    subprocess.run(["git", "add", "-A"], cwd=workdir, capture_output=True)
    subprocess.run(["git", "commit", "-m", message, "--allow-empty"], cwd=workdir, capture_output=True)


# ── Message serialization ────────────────────────────────────────────

def _serialize_assistant_message(msg) -> dict:
    """
    Convert the OpenAI SDK message object to a dict for the message history.
    Handles the `reasoning` field which the model returns but shouldn't be
    sent back in the conversation history.
    """
    result = {"role": "assistant"}

    if msg.content:
        result["content"] = msg.content
    else:
        result["content"] = None

    if msg.tool_calls:
        result["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]

    return result


# ── Main agent loop ───────────────────────────────────────────────────

def run_agent(task: str, workdir: Path, cfg: Config, verbose: bool = True) -> list:
    """
    Run the agent loop for a single task.

    Args:
        task: Natural-language task description
        workdir: Repository directory to operate in
        cfg: Agent configuration
        verbose: Whether to print detailed output

    Returns:
        The full message history
    """
    workdir = workdir.resolve()
    _ensure_git(workdir)

    client = OpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        timeout=httpx.Timeout(300.0, connect=10.0),
    )
    dispatch = make_dispatch(workdir)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]
    _checkpoint(workdir, "checkpoint: start")

    if verbose:
        if HAS_RICH:
            console.rule("[bold blue]Agent Started[/bold blue]")
            console.print(f"📋 Task: {task}", style="bold")
            console.print(f"📂 Workdir: {workdir}", style="dim")
            console.print(f"🌐 Endpoint: {cfg.base_url}", style="dim")
            console.print(f"🤖 Model: {cfg.model}", style="dim")
        else:
            console.rule("Agent Started")
            console.print(f"📋 Task: {task}")
            console.print(f"📂 Workdir: {workdir}")

    for turn in range(cfg.max_turns):
        if verbose:
            if HAS_RICH:
                console.rule(f"[bold]Turn {turn + 1}[/bold]", style="blue")
            else:
                console.rule(f"Turn {turn + 1}")

        try:
            resp = client.chat.completions.create(
                model=cfg.model,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                temperature=cfg.temperature,
                max_tokens=cfg.max_tokens,
                extra_body={"chat_template_kwargs": {"enable_thinking": True}},
            )
        except Exception as e:
            if verbose:
                console.print(f"❌ API error: {e}", style="bold red")
            raise

        msg = resp.choices[0].message

        # Display reasoning if present
        reasoning = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
        if verbose and reasoning:
            _print_reasoning(reasoning)

        # Serialize and append assistant message to history
        messages.append(_serialize_assistant_message(msg))

        # Handle tool calls
        if msg.tool_calls:
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                if verbose:
                    _print_tool_call(turn, tc.function.name, args)
                try:
                    result = dispatch[tc.function.name](args)
                except Exception as e:
                    result = f"error: {e}"
                if verbose:
                    _print_tool_result(result)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(result),
                })
            _checkpoint(workdir, f"checkpoint: turn {turn + 1}")
            continue

        # Handle text response
        if msg.content:
            if verbose:
                _print_assistant_message(msg.content)
            if msg.content.strip().startswith("DONE"):
                _checkpoint(workdir, "checkpoint: done")
                if verbose and HAS_RICH:
                    console.rule("[bold green]✅ Task Complete[/bold green]")
                return messages
        else:
            # Model returned empty content — check if DONE is in reasoning (common issue)
            if reasoning and "DONE:" in reasoning:
                done_text = reasoning[reasoning.index("DONE:"):].strip()
                if verbose:
                    _print_assistant_message(done_text)
                _checkpoint(workdir, "checkpoint: done")
                if verbose and HAS_RICH:
                    console.rule("[bold green]✅ Task Complete[/bold green]")
                return messages
            if verbose:
                console.print("⚠️  Model returned empty response (may have exhausted tokens on reasoning). Retrying...", style="yellow")
            # Remove the empty assistant message and retry
            messages.pop()
            continue

    if verbose:
        console.print(f"\n⚠️  Max turns ({cfg.max_turns}) reached without completion.", style="bold yellow")
    return messages


def run_chat(workdir: Path, cfg: Config, verbose: bool = True) -> None:
    """
    Interactive chat REPL mode. Multi-turn conversation with the agent.
    """
    workdir = workdir.resolve()
    _ensure_git(workdir)

    client = OpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        timeout=httpx.Timeout(300.0, connect=10.0),
    )
    dispatch = make_dispatch(workdir)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]

    if HAS_RICH:
        console.print()
        console.print(Panel(
            "[bold cyan]AlpieCode[/bold cyan] interactive mode\n"
            f"📂 Working in: [cyan]{workdir}[/cyan]\n"
            f"🤖 Model: [cyan]{cfg.model}[/cyan]\n\n"
            "Type your request, or [bold red]exit[/bold red] / [bold red]quit[/bold red] to stop.",
            title="💬 Chat Mode",
            border_style="blue",
        ))
    else:
        console.print("\n💬 Chat Mode — type your request, or 'exit' to stop.")
        console.print(f"📂 Working in: {workdir}")

    turn_count = 0

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

        messages.append({"role": "user", "content": user_input})

        # Inner loop: keep going until the model gives a text reply (not just tool calls)
        for _ in range(cfg.max_turns):
            turn_count += 1
            if verbose:
                if HAS_RICH:
                    console.rule(f"[bold]Turn {turn_count}[/bold]", style="blue")
                else:
                    console.rule(f"Turn {turn_count}")

            try:
                resp = client.chat.completions.create(
                    model=cfg.model,
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                    extra_body={"chat_template_kwargs": {"enable_thinking": True}},
                )
            except Exception as e:
                console.print(f"❌ API error: {e}", style="bold red" if HAS_RICH else None)
                break

            msg = resp.choices[0].message

            reasoning = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)
            if verbose and reasoning:
                _print_reasoning(reasoning)

            messages.append(_serialize_assistant_message(msg))

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    args = json.loads(tc.function.arguments or "{}")
                    if verbose:
                        _print_tool_call(turn_count, tc.function.name, args)
                    try:
                        result = dispatch[tc.function.name](args)
                    except Exception as e:
                        result = f"error: {e}"
                    if verbose:
                        _print_tool_result(result)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": str(result),
                    })
                _checkpoint(workdir, f"checkpoint: chat turn {turn_count}")
                continue

            if msg.content:
                _print_assistant_message(msg.content)
                if msg.content.strip().startswith("DONE"):
                    _checkpoint(workdir, "checkpoint: done")
                break
            else:
                # Check if DONE is in reasoning (model sometimes puts it there)
                if reasoning and "DONE:" in reasoning:
                    done_text = reasoning[reasoning.index("DONE:"):].strip()
                    _print_assistant_message(done_text)
                    _checkpoint(workdir, "checkpoint: done")
                    break
                if verbose:
                    console.print("⚠️  Empty response, retrying...", style="yellow" if HAS_RICH else None)
                messages.pop()
                continue
