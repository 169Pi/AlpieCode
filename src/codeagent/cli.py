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


def _normalize_args():
    known_commands = {"init", "serve", "run", "chat", "plan", "diff", "doctor", "explain", "-h", "--help", "--version"}
    subcommand = None
    
    # Check if a subcommand is present
    for arg in sys.argv[1:]:
        if arg in known_commands:
            subcommand = arg
            break
            
    if not subcommand and len(sys.argv) > 1:
        subcommand = "run"
        sys.argv.insert(1, "run")

    if subcommand in ("run", "plan", "explain") and len(sys.argv) > 2:
        cmd_idx = sys.argv.index(subcommand)
        sub_args = sys.argv[cmd_idx + 1:]
        
        flags = []
        positionals = []
        value_flags = {"--workdir", "--image", "--video", "--url", "--github", "--max-turns", "--host", "--port"}
        
        i = 0
        while i < len(sub_args):
            arg = sub_args[i]
            if arg.startswith("-"):
                flags.append(arg)
                if "=" in arg:
                    pass  # e.g. --complexity=low already contains its value
                elif arg in value_flags and i + 1 < len(sub_args) and not sub_args[i + 1].startswith("-"):
                    flags.append(sub_args[i + 1])
                    i += 1
            else:
                positionals.append(arg)
            i += 1
            
        sys.argv = sys.argv[:cmd_idx + 1] + flags + positionals


def main():
    _normalize_args()

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workdir", default=".", help="Repo directory (default: current dir)")
    common.add_argument("--image", default=None, help="Path to an image file for vision analysis")
    common.add_argument("--video", default=None, help="Path to a video file for multimodal analysis")
    common.add_argument("--url", default=None, help="YouTube URL for video analysis")
    common.add_argument("--github", default=None, help="GitHub repository (e.g. owner/repo or URL) for open-source analysis")
    common.add_argument("--max-turns", type=int, default=None, help="Override max turns")
    common.add_argument("--thinking", "--reasoning", dest="thinking", action="store_true", help="Enable VLM reasoning mode")
    common.add_argument("--no-thinking", "--non-thinking", dest="no_thinking", action="store_true", help="Disable VLM reasoning mode")
    common.add_argument("--no-update", action="store_true", help="Skip automatic update check")
    common.add_argument("--quiet", action="store_true", help="Suppress per-turn logging")
    common.add_argument("--debug", action="store_true", help="Show autonomous discovery and debug diagnostics")

    parser = argparse.ArgumentParser(
        prog="alpiecode",
        description="AlpieCode — Autonomous AI Coding Agent powered by 169Pi Alpie VLM",
        parents=[common],
    )
    sub = parser.add_subparsers(dest="command")

    # ── init ──
    sub.add_parser("init", help="Configure your VLM/OpenAI-compatible endpoint")

    # ── serve ──
    serve_p = sub.add_parser("serve", help="Start the AlpieCode API server")
    serve_p.add_argument("--host", default="127.0.0.1", help="Host address to bind to (default: 127.0.0.1)")
    serve_p.add_argument("--port", type=int, default=7169, help="Port to listen on (default: 7169)")

    # ── run ──
    run_p = sub.add_parser("run", help="Run a coding task against a repository", parents=[common])
    run_p.add_argument("task", help="Natural-language task description")

    # ── chat ──
    chat_p = sub.add_parser("chat", help="Interactive chat mode with AlpieCode", parents=[common])

    # ── plan ──
    plan_p = sub.add_parser("plan", help="Generate a plan without making changes (read-only)", parents=[common])
    plan_p.add_argument("task", help="Natural-language task to plan for")

    # ── diff ──
    diff_p = sub.add_parser("diff", help="Show changes AlpieCode has made since last checkpoint", parents=[common])

    # ── doctor ──
    sub.add_parser("doctor", help="Run system health checks (CUDA, Python, network, dev tools)")

    # ── explain ──
    explain_p = sub.add_parser("explain", help="Explain a file, function, or codebase concept", parents=[common])
    explain_p.add_argument("target", help="File path or concept to explain")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "init":
        interactive_init()
        return

    if args.command == "doctor":
        from .doctor import run_doctor
        sys.exit(run_doctor())

    if args.command == "serve":
        _show_banner()
        try:
            from .vscode_installer import ensure_vscode_extension
            ensure_vscode_extension()
        except Exception as e:
            pass
        from .server import run_server
        run_server(host=args.host, port=args.port)
        return

    # Check for auto-updates from GitHub in background
    if not getattr(args, "no_update", False):
        try:
            from .updater import auto_update
            auto_update(quiet=getattr(args, "quiet", False))
        except Exception:
            pass

    cfg = load_config()

    if getattr(args, "thinking", False):
        cfg.enable_thinking = True
    elif getattr(args, "no_thinking", False):
        cfg.enable_thinking = False

    if args.command == "run":
        if args.max_turns:
            cfg.max_turns = args.max_turns
        _show_banner()
        from .agent import run_agent
        run_agent(
            args.task, Path(args.workdir), cfg,
            verbose=not args.quiet,
            image_path=args.image,
            video_path=getattr(args, "video", None),
            url=getattr(args, "url", None),
            github_repo=getattr(args, "github", None),
            debug=getattr(args, "debug", False),
        )

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
        run_agent(
            plan_task, Path(args.workdir), cfg, verbose=True,
            image_path=args.image,
            video_path=getattr(args, "video", None),
            url=getattr(args, "url", None),
            github_repo=getattr(args, "github", None),
            debug=getattr(args, "debug", False),
        )

    elif args.command == "doctor":
        from .doctor import run_doctor
        sys.exit(run_doctor())

    elif args.command == "explain":
        _show_banner()
        target = args.target
        target_path = Path(args.workdir) / target if not Path(target).is_absolute() else Path(target)
        if target_path.exists() and target_path.is_file():
            content = target_path.read_text(encoding="utf-8", errors="replace")
            explain_task = (
                f"EXPLANATION ONLY — Do NOT make any file edits or run modifying commands.\n\n"
                f"Please explain the file `{target}` in detail:\n"
                f"1. Overview of its purpose and architecture role\n"
                f"2. Key functions, classes, and internal logic\n"
                f"3. Dependencies and connections to the rest of the project\n"
                f"4. Step-by-step walkthrough of how it operates\n\n"
                f"File content ({target}):\n```\n{content[:16000]}\n```"
            )
        else:
            explain_task = (
                f"EXPLANATION ONLY — Do NOT make any file edits.\n\n"
                f"Explain the following codebase concept, architecture, or question in detail:\n"
                f"Topic: {target}\n\n"
                f"Use read_file, file_search, or list_files if needed to understand the codebase context."
            )
        from .agent import run_agent
        run_agent(
            explain_task, Path(args.workdir), cfg, verbose=True,
            image_path=args.image,
            video_path=getattr(args, "video", None),
            url=getattr(args, "url", None),
            github_repo=getattr(args, "github", None),
            debug=getattr(args, "debug", False),
        )

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
