"""
Auto-updater module for AlpieCode.

Checks GitHub repo (https://api.github.com/repos/169Pi/AlpieCode/commits/main)
and automatically updates AlpieCode in the background if a newer commit exists.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CACHE_FILE = Path.home() / ".alpiecode" / "update_cache.json"
CHECK_INTERVAL_SECONDS = 3600  # Check at most once per hour to stay fast


def _get_installed_sha() -> str:
    """Read cached commit SHA or return empty string."""
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            return data.get("sha", "")
        except Exception:
            pass
    return ""


def _save_cache(sha: str) -> None:
    """Save last checked commit SHA and timestamp."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({
            "sha": sha,
            "timestamp": time.time()
        }))
    except Exception:
        pass


def auto_update(quiet: bool = False) -> bool:
    """
    Check for updates on GitHub and auto-upgrade AlpieCode if a new version is available.
    Returns True if an update was performed.
    """
    if os.environ.get("ALPIECODE_NO_UPDATE") == "1":
        return False

    # Check if we checked recently (within last 1 hour)
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            last_check = data.get("timestamp", 0)
            if time.time() - last_check < CHECK_INTERVAL_SECONDS:
                return False
        except Exception:
            pass

    # Fetch latest commit SHA from GitHub API (timeout 2.5s to never block user)
    try:
        url = "https://api.github.com/repos/169Pi/AlpieCode/commits/main"
        req = urllib.request.Request(url, headers={"User-Agent": "AlpieCode-Updater"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latest_sha = data.get("sha", "")
    except Exception:
        # Offline or GitHub API rate-limited — skip silently
        return False

    current_sha = _get_installed_sha()
    if latest_sha and latest_sha != current_sha:
        if not quiet:
            try:
                from rich.console import Console
                Console().print("🔄 [bold cyan]AlpieCode auto-updater:[bold cyan] New updates found on GitHub! Upgrading...", highlight=False)
            except ImportError:
                print("🔄 AlpieCode auto-updater: New updates found on GitHub! Upgrading...")

        # Determine python / uv executable
        repo_url = "git+https://github.com/169Pi/AlpieCode.git"
        
        # Try uv pip install --upgrade first, fallback to pip install --upgrade
        cmd = ["uv", "pip", "install", "--upgrade", "--quiet", repo_url]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if res.returncode != 0:
                # Fallback to sys.executable -m pip install --upgrade
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "--quiet", repo_url]
                subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except Exception:
            pass

        _save_cache(latest_sha)
        if not quiet:
            try:
                from rich.console import Console
                Console().print("✨ [bold green]Updated successfully![/bold green]\n", highlight=False)
            except ImportError:
                print("✨ Updated successfully!\n")
        return True

    _save_cache(latest_sha or current_sha)
    return False
