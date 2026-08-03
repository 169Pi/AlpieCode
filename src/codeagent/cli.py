"""
CLI entry point for AlpieCode.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from .config import CONFIG_PATH, interactive_init, load_config


BANNER = r"""
    _    _     _      ____            _      
   / \  | |_ _| | ___ / ___|___   __| | ___ 
  / _ \ | | '_ \ |/ _ \ |   / _ \ / _` |/ _ \
 / ___ \| | |_) | |  __/ |__| (_) | (_| |  __/
/_/   \_\_|_.__/|_|\___|\____\___/ \__,_|\___|
"""


def _show_banner():
    try:
        from rich.console import Console
        console = Console()
        console.print(BANNER, style="bold cyan", highlight=False)
    except ImportError:
        print(BANNER)


def main():
    # Auto-insert 'run' if user types `alpiecode "task"` without subcommand
    if len(sys.argv) > 1 and sys.argv[1] not in (
        "init", "run", "chat", "plan", "diff", "-h", "--help", "--version"
    ):
        sys.argv.insert(1, "run")

    parser = argparse.ArgumentParser(
        prog="alpiecode",
        description="AlpieCode — Autonomous AI Coding Agent powered by 169Pi Alpie VLM",
    )
    sub = parser.add_subparsers(dest="command")

    # ── init ──
    sub.add_parser("init", help="Configure your VLM/OpenAI-compatible endpoint")

    # ── run ──
    run_p = sub.add_parser("run", help="Run a coding task against a repository")
    run_p.add_argument("task", help="Natural-language task description")
    run_p.add_argument("--workdir", default=".", help="Repo directory (default: current dir)")
    run_p.add_argument("--image", default=None, help="Path to an image file for vision analysis")
    run_p.add_argument("--max-turns", type=int, default=None, help="Override max turns")
    run_p.add_argument("--no-thinking", action="store_true", help="Disable VLM reasoning/thinking mode")
    run_p.add_argument("--quiet", action="store_true", help="Suppress per-turn logging")

    # ── chat ──
    chat_p = sub.add_parser("chat", help="Interactive chat mode with AlpieCode")
    chat_p.add_argument("--workdir", default=".", help="Repo directory (default: current dir)")
    chat_p.add_argument("--max-turns", type=int, default=None, help="Override max turns per message")
    chat_p.add_argument("--no-thinking", action="store_true", help="Disable VLM reasoning/thinking mode")
    chat_p.add_argument("--quiet", action="store_true", help="Suppress per-turn logging")

    # ── plan ──
    plan_p = sub.add_parser("plan", help="Generate a plan without making changes (read-only)")
    plan_p.add_argument("task", help="Natural-language task to plan for")
    plan_p.add_argument("--workdir", default=".", help="Repo directory (default: current dir)")
    plan_p.add_argument("--image", default=None, help="Path to an image file for vision analysis")

    # ── diff ──
    diff_p = sub.add_parser("diff", help="Show changes AlpieCode has made since last checkpoint")
    diff_p.add_argument("--workdir", default=".", help="Repo directory (default: current dir)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "init":
        interactive_init()
        return

    cfg = load_config()

    if getattr(args, "no_thinking", False):
        cfg.enable_thinking = False

    if args.command == "run":
        if args.max_turns:
            cfg.max_turns = args.max_turns
        _show_banner()
        from .agent import run_agent
        run_agent(args.task, Path(args.workdir), cfg, verbose=not args.quiet, image_path=args.image)

    elif args.command == "chat":
        if args.max_turns:
            cfg.max_turns = args.max_turns
        _show_banner()
        from .agent import run_chat
        run_chat(Path(args.workdir), cfg, verbose=not args.quiet)

    elif args.command == "plan":
        _show_banner()
        plan_task = (
            f"PLANNING ONLY — Do NOT make any file edits. "
            f"Analyze the codebase and create a detailed implementation plan for the following task. "
            f"Use list_files, read_file, and file_search to understand the project. "
            f"Then use update_plan to write a structured plan with deliverables and checks. "
            f"Finish with DONE: when the plan is complete.\n\n"
            f"Task: {args.task}"
        )
        from .agent import run_agent
        run_agent(plan_task, Path(args.workdir), cfg, verbose=True, image_path=args.image)

    elif args.command == "diff":
        workdir = Path(args.workdir).resolve()
        # Show git diff since the first checkpoint
        result = subprocess.run(
            ["git", "log", "--oneline", "--all"],
            cwd=workdir, capture_output=True, text=True
        )
        if result.returncode != 0:
            print("Not a git repository or no commits found.")
            return

        # Find the start checkpoint
        log_lines = result.stdout.strip().splitlines()
        start_sha = None
        for line in reversed(log_lines):
            if "checkpoint: start" in line:
                start_sha = line.split()[0]
                break

        if not start_sha:
            print("No AlpieCode checkpoint found. Run a task first.")
            return

        diff_result = subprocess.run(
            ["git", "diff", start_sha, "HEAD", "--stat"],
            cwd=workdir, capture_output=True, text=True
        )
        print(f"Changes since AlpieCode started (from {start_sha}):\n")
        print(diff_result.stdout)

        # Also show the full diff
        full_diff = subprocess.run(
            ["git", "diff", start_sha, "HEAD"],
            cwd=workdir, capture_output=True, text=True
        )
        if full_diff.stdout:
            try:
                from rich.console import Console
                from rich.syntax import Syntax
                console = Console()
                syntax = Syntax(full_diff.stdout, "diff", theme="monokai")
                console.print(syntax)
            except ImportError:
                print(full_diff.stdout)


if __name__ == "__main__":
    main()
