"""
Git session tracking, diff inspection, and safe rollback for AlpieCode.

Features:
- Track files created / modified per session
- `show_diff()`: Render colorized, syntax-highlighted diffs of uncommitted agent changes
- `undo_last_session()`: Cleanly revert all changes made during the last agent session
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import List, Set, Optional, Dict, Any

from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

SESSION_FILE = ".alpiecode_session.json"


def record_session_start(workdir: Path) -> Dict[str, Any]:
    """Capture initial git / filesystem state before agent execution begins."""
    state: Dict[str, Any] = {
        "is_git": False,
        "initial_status": {},
        "created_files": [],
        "modified_files": [],
    }

    if shutil.which("git") and (workdir / ".git").exists():
        try:
            res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=workdir, capture_output=True, text=True, timeout=5
            )
            if res.returncode == 0:
                state["is_git"] = True
                status_dict = {}
                for line in res.stdout.splitlines():
                    if len(line) >= 4:
                        st = line[:2].strip()
                        f = line[3:].strip()
                        status_dict[f] = st
                state["initial_status"] = status_dict
        except Exception:
            pass

    return state


def record_session_end(workdir: Path, state: Dict[str, Any], touched_files: Set[str]):
    """Save the session outcome to allow diffing and rolling back."""
    session_data = {
        "is_git": state.get("is_git", False),
        "touched_files": list(touched_files),
        "initial_status": state.get("initial_status", {}),
    }

    # Determine which files were newly created vs modified
    created = []
    modified = []

    init_status = state.get("initial_status", {})
    for f in touched_files:
        full_p = workdir / f
        if not full_p.exists():
            continue
        if f not in init_status:
            # Was not tracked or did not exist before
            created.append(f)
        else:
            modified.append(f)

    session_data["created_files"] = created
    session_data["modified_files"] = modified

    try:
        (workdir / SESSION_FILE).write_text(json.dumps(session_data, indent=2), encoding="utf-8")
    except Exception:
        pass


def show_diff(workdir: Path):
    """Render colorized Rich diff of changes made since last session."""
    console = Console()
    sess_path = workdir / SESSION_FILE

    # If git repo, run git diff
    if shutil.which("git") and (workdir / ".git").exists():
        try:
            res = subprocess.run(
                ["git", "diff"],
                cwd=workdir, capture_output=True, text=True, timeout=8
            )
            diff_text = res.stdout.strip()
            if diff_text:
                console.print(Panel(
                    Syntax(diff_text, "diff", theme="monokai", line_numbers=False),
                    title="🔍 AlpieCode Session Diff",
                    border_style="cyan"
                ))
                return
        except Exception:
            pass

    # Fallback to session record
    if sess_path.exists():
        try:
            data = json.loads(sess_path.read_text(encoding="utf-8"))
            created = data.get("created_files", [])
            modified = data.get("modified_files", [])

            if not created and not modified:
                console.print("[green]✨ Clean workspace — no files modified by the last session.[/green]")
                return

            console.print("[bold cyan]Session File Changes:[/bold cyan]")
            for c in created:
                console.print(f"  [green]+ created:[/green] {c}")
            for m in modified:
                console.print(f"  [yellow]~ modified:[/yellow] {m}")
            return
        except Exception:
            pass

    console.print("[green]✨ Clean workspace — no changes found.[/green]")


def undo_last_session(workdir: Path) -> bool:
    """Revert changes made during the last agent session."""
    console = Console()
    sess_path = workdir / SESSION_FILE

    if not sess_path.exists():
        # If in a git repo, check uncommitted changes
        if shutil.which("git") and (workdir / ".git").exists():
            try:
                res = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=workdir, capture_output=True, text=True, timeout=5
                )
                if not res.stdout.strip():
                    console.print("[green]✨ Nothing to undo — working directory is already clean.[/green]")
                    return True

                console.print("[yellow]Found uncommitted git changes:[/yellow]")
                for line in res.stdout.splitlines()[:10]:
                    console.print(f"  {line}")

                choice = input("\nRevert all uncommitted changes? [y/N]: ").strip().lower()
                if choice in ("y", "yes"):
                    subprocess.run(["git", "restore", "."], cwd=workdir, check=True)
                    subprocess.run(["git", "clean", "-fd"], cwd=workdir, check=True)
                    console.print("[green]✅ Successfully reverted all uncommitted changes![/green]")
                    return True
                else:
                    console.print("[dim]Undo canceled.[/dim]")
                    return False
            except Exception as e:
                console.print(f"[red]Error during git undo: {e}[/red]")
                return False

        console.print("[yellow]No recent AlpieCode session found to undo.[/yellow]")
        return False

    try:
        data = json.loads(sess_path.read_text(encoding="utf-8"))
        created = data.get("created_files", [])
        modified = data.get("modified_files", [])

        if not created and not modified:
            console.print("[green]✨ Nothing to undo — no files were touched in the last session.[/green]")
            return True

        console.print("[bold red]Files to revert:[/bold red]")
        for c in created:
            console.print(f"  [red]- remove created:[/red] {c}")
        for m in modified:
            console.print(f"  [yellow]↺ restore modified:[/yellow] {m}")

        choice = input("\nRevert these changes? [y/N]: ").strip().lower()
        if choice not in ("y", "yes"):
            console.print("[dim]Undo canceled.[/dim]")
            return False

        # Revert modified files via git if possible
        if data.get("is_git") and shutil.which("git"):
            for m in modified:
                try:
                    subprocess.run(["git", "checkout", "--", m], cwd=workdir, check=False)
                except Exception:
                    pass

        # Remove created files
        for c in created:
            p = workdir / c
            if p.exists() and p.is_file():
                try:
                    p.unlink()
                except Exception:
                    pass

        # Clean up session file
        sess_path.unlink(missing_ok=True)
        console.print(f"[green]✅ Successfully reverted {len(created) + len(modified)} files![/green]")
        return True

    except Exception as e:
        console.print(f"[red]Failed to undo session: {e}[/red]")
        return False


def push_to_remote(workdir: Path, username: Optional[str] = None, branch: Optional[str] = None) -> Dict[str, Any]:
    """Stage, commit, and push changes to git remote origin."""
    if not shutil.which("git") or not (workdir / ".git").exists():
        return {"success": False, "error": "Not a git repository"}

    try:
        # Check remote
        rem_res = subprocess.run(["git", "remote", "get-url", "origin"], cwd=workdir, capture_output=True, text=True, timeout=5)
        if rem_res.returncode != 0:
            return {"success": False, "error": "No remote 'origin' configured"}
        remote_url = rem_res.stdout.strip()

        # Determine branch
        if not branch:
            br_res = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=workdir, capture_output=True, text=True, timeout=5)
            branch = br_res.stdout.strip() if br_res.returncode == 0 else "main"

        # Stage and commit any uncommitted changes
        subprocess.run(["git", "add", "-A"], cwd=workdir, capture_output=True, timeout=10)
        commit_cmd = ["git"]
        if username:
            commit_cmd.extend(["-c", f"user.name={username}"])
        commit_cmd.extend(["commit", "-m", "feat: updates by AlpieCode agent", "--allow-empty"])
        subprocess.run(commit_cmd, cwd=workdir, capture_output=True, timeout=10)

        # Push to origin
        push_res = subprocess.run(["git", "push", "-u", "origin", branch], cwd=workdir, capture_output=True, text=True, timeout=30)
        if push_res.returncode == 0:
            return {
                "success": True,
                "remote": remote_url,
                "branch": branch,
                "username": username or "default",
                "output": push_res.stdout.strip() or push_res.stderr.strip(),
            }
        else:
            return {"success": False, "error": push_res.stderr.strip()}

    except Exception as e:
        return {"success": False, "error": str(e)}
