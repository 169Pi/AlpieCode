"""
CLI entry point for codeagent.
"""

import argparse
import sys
from pathlib import Path

from .config import CONFIG_PATH, interactive_init, load_config


BANNER = r"""
   ___          _         _                    _
  / __\___   __| | ___   / \   __ _  ___ _ __ | |_
 / /  / _ \ / _` |/ _ \ /  /\ / _` |/ _ \ '_ \| __|
/ /__| (_) | (_| |  __// /_// (_| |  __/ | | | |_
\____/\___/ \__,_|\___/\___,' \__, |\___|_| |_|\__|
                              |___/
"""


def main():
    parser = argparse.ArgumentParser(
        prog="codeagent",
        description="Coding agent CLI backed by your own VLM endpoint",
    )
    sub = parser.add_subparsers(dest="command")

    # ── init ──
    sub.add_parser("init", help="Configure your VLM/OpenAI-compatible endpoint")

    # ── run ──
    run_p = sub.add_parser("run", help="Run a coding task against a repo")
    run_p.add_argument("task", help="Natural-language task description")
    run_p.add_argument("--workdir", default=".", help="Repo directory to operate in (default: current dir)")
    run_p.add_argument("--max-turns", type=int, default=None, help="Override configured max turns")
    run_p.add_argument("--quiet", action="store_true", help="Suppress per-turn logging")

    # ── chat ──
    chat_p = sub.add_parser("chat", help="Interactive chat mode with the agent")
    chat_p.add_argument("--workdir", default=".", help="Repo directory to operate in (default: current dir)")
    chat_p.add_argument("--max-turns", type=int, default=None, help="Override configured max turns per message")
    chat_p.add_argument("--quiet", action="store_true", help="Suppress per-turn logging")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "init":
        interactive_init()
        return

    # Load config — works with defaults even without init
    cfg = load_config()

    if args.command == "run":
        if args.max_turns:
            cfg.max_turns = args.max_turns

        try:
            from rich.console import Console
            console = Console()
            console.print(BANNER, style="bold blue", highlight=False)
        except ImportError:
            print(BANNER)

        from .agent import run_agent
        run_agent(args.task, Path(args.workdir), cfg, verbose=not args.quiet)

    elif args.command == "chat":
        if args.max_turns:
            cfg.max_turns = args.max_turns

        try:
            from rich.console import Console
            console = Console()
            console.print(BANNER, style="bold blue", highlight=False)
        except ImportError:
            print(BANNER)

        from .agent import run_chat
        run_chat(Path(args.workdir), cfg, verbose=not args.quiet)


if __name__ == "__main__":
    main()
