"""
Guardian — lightweight command safety gate for AlpieCode.

Classifies bash commands into risk levels before execution:
  - SAFE: read-only commands (ls, cat, grep, git status, python -m pytest, etc.)
  - WARNING: potentially destructive but common (rm, pip install, chmod, etc.)
  - DANGEROUS: extremely risky commands that require explicit user confirmation

This is a pattern-matching heuristic, not an LLM call — fast and deterministic.
"""

import re
from enum import Enum
from typing import Tuple

try:
    from rich.console import Console
    from rich.panel import Panel
    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


class RiskLevel(Enum):
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"


# ── Pattern definitions ───────────────────────────────────────────────

# Commands that are always safe (read-only operations)
SAFE_PREFIXES = [
    "ls", "cat", "head", "tail", "wc", "file", "stat", "du", "df",
    "pwd", "whoami", "uname", "date", "echo", "printf", "which", "where",
    "find", "locate", "grep", "egrep", "fgrep", "rg", "ag",
    "git status", "git log", "git diff", "git show", "git branch",
    "git remote", "git tag", "git stash list", "git rev-parse",
    "python --version", "python3 --version", "node --version",
    "npm --version", "pip --version", "pip3 --version",
    "python -m pytest", "python3 -m pytest", "pytest", "npm test",
    "npm run test", "make test", "cargo test", "go test",
    "python -c", "python3 -c", "node -e",
    "tree", "sort", "uniq", "cut", "awk", "sed -n", "diff",
    "env", "printenv", "set",
    "type", "command -v",
    "uv pip install", "uv pip", "uv venv", "uv run", "uv sync",
]

# Commands that are potentially destructive but commonly used
WARNING_PATTERNS = [
    r"\brm\b(?!\s+-rf\s+[/~])",        # rm but not rm -rf / or ~
    r"\bchmod\b", r"\bchown\b",
    r"\bpip install\b", r"\bpip3 install\b",
    r"\bnpm install\b", r"\byarn add\b", r"\bpnpm add\b",
    r"\bgit add\b", r"\bgit commit\b", r"\bgit push\b",
    r"\bgit checkout\b", r"\bgit reset\b", r"\bgit rebase\b",
    r"\bgit merge\b", r"\bgit stash\b",
    r"\bmv\b", r"\bcp\b",
    r"\bmkdir\b", r"\btouch\b",
    r"\bkill\b", r"\bkillall\b",
    r"\bapt install\b", r"\bapt-get install\b",
    r"\bbrew install\b",
    r"\bdocker\b",
]

# Commands that should be blocked without explicit confirmation
DANGEROUS_PATTERNS = [
    r"\brm\s+-rf\s+[/~]",              # rm -rf / or rm -rf ~
    r"\brm\s+-rf\s+\*",                # rm -rf *
    r"\bsudo\b",                        # anything with sudo
    r"\bmkfs\b", r"\bfdisk\b",         # filesystem manipulation
    r"\bdd\s+if=", r"\bdd\s+of=",      # raw disk operations
    r":\(\)\s*\{", r"fork\s*bomb",     # fork bombs
    r"\bcurl\b.*\|\s*(?:ba)?sh",       # curl | bash (piped execution)
    r"\bwget\b.*\|\s*(?:ba)?sh",       # wget | bash
    r"\b>\s*/dev/sd",                   # write to raw devices
    r"\bshutdown\b", r"\breboot\b",    # system control
    r"\binit\s+[0-6]\b",               # runlevel changes
    r"\bsystemctl\s+(?:stop|disable|mask)\b",
    r"\bchmod\s+777\s+/",              # world-writable root
    r"\beval\b.*\$\(",                  # eval with command substitution
    r">\s*/etc/",                       # overwrite system configs
    r"\bexport\s+.*(?:KEY|SECRET|TOKEN|PASSWORD)", # leaking secrets
]


def classify_command(command: str) -> Tuple[RiskLevel, str]:
    """
    Classify a shell command by risk level.

    Returns:
        Tuple of (RiskLevel, reason_string)
    """
    cmd_lower = command.strip().lower()

    # Check dangerous first (highest priority)
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_lower):
            return RiskLevel.DANGEROUS, f"Matches dangerous pattern: {pattern}"

    # Check safe prefixes
    for prefix in SAFE_PREFIXES:
        if cmd_lower.startswith(prefix):
            return RiskLevel.SAFE, f"Read-only command: {prefix}"

    # Check warning patterns
    for pattern in WARNING_PATTERNS:
        if re.search(pattern, cmd_lower):
            return RiskLevel.WARNING, f"Potentially destructive: {pattern}"

    # Default: treat unknown commands as warning
    return RiskLevel.WARNING, "Unknown command — proceeding with caution"


def gate_command(command: str, auto_approve: bool = False) -> bool:
    """
    Gate a command through the safety system.

    Args:
        command: The shell command to evaluate
        auto_approve: If True, auto-approve SAFE and WARNING (skip prompts)

    Returns:
        True if the command should be executed, False if blocked
    """
    risk, reason = classify_command(command)

    if risk == RiskLevel.SAFE:
        return True

    if risk == RiskLevel.WARNING:
        if auto_approve:
            if HAS_RICH:
                console.print(f"   ⚠️  [yellow]{reason}[/yellow]", highlight=False)
            return True
        # In interactive mode, show warning but proceed
        if HAS_RICH:
            console.print(f"   ⚠️  [yellow]{reason}[/yellow]", highlight=False)
        return True

    if risk == RiskLevel.DANGEROUS:
        if HAS_RICH:
            console.print(Panel(
                f"[bold red]🛑 BLOCKED — Dangerous Command[/bold red]\n\n"
                f"Command: [cyan]{command}[/cyan]\n"
                f"Reason: {reason}\n\n"
                f"This command has been blocked for safety.\n"
                f"If you need to run it, do so manually in your terminal.",
                border_style="red",
            ))
        else:
            print(f"\n🛑 BLOCKED — Dangerous Command")
            print(f"   Command: {command}")
            print(f"   Reason: {reason}")
        return False

    return True
