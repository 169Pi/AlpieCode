"""
Auto-updater module for AlpieCode.

Checks GitHub repo (https://api.github.com/repos/169Pi/AlpieCode/commits/main)
and automatically updates AlpieCode in the background if a newer commit exists.

Updates are installed silently via background thread so CLI startup is instant.
The updated code takes effect on the NEXT run.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import threading

CACHE_FILE = Path.home() / ".alpiecode" / "update_cache.json"
CHECK_INTERVAL_SECONDS = 1800  # Check every 30 minutes


def _get_cache() -> dict:
    """Read update cache data."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_cache(sha: str, updated: bool = False) -> None:
    """Save last checked commit SHA and timestamp."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps({
            "sha": sha,
            "timestamp": time.time(),
            "updated": updated,
        }))
    except Exception:
        pass


def _check_pending_update_notice() -> None:
    """Print a notice if an update was installed in a previous run."""
    cache = _get_cache()
    if cache.get("updated"):
        short_sha = cache.get("sha", "")[:7]
        print(f"  ✅ AlpieCode auto-updated to latest ({short_sha})")
        # Clear the flag so we don't show it again
        _save_cache(cache.get("sha", ""), updated=False)


def _detect_install_extras() -> str:
    """Detect if llama-cpp-python is installed to preserve [local] extras."""
    try:
        import llama_cpp  # noqa: F401
        return "[local]"
    except ImportError:
        return ""


def _bg_update_worker(quiet: bool = False) -> None:
    """Background worker: check GitHub for new commits and auto-upgrade."""
    try:
        url = "https://api.github.com/repos/169Pi/AlpieCode/commits/main"
        req = urllib.request.Request(url, headers={"User-Agent": "AlpieCode-Updater"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latest_sha = data.get("sha", "")
    except Exception:
        return

    cache = _get_cache()
    current_sha = cache.get("sha", "")

    if latest_sha and latest_sha != current_sha:
        # Detect if user has [local] extras installed
        extras = _detect_install_extras()
        repo_url = f"git+https://github.com/169Pi/AlpieCode.git@main"
        # If user has llama-cpp-python, we install without extras to avoid rebuilding C++
        # The [local] extra would try to rebuild llama-cpp-python from source

        # Try uv first (faster), fall back to pip
        cmd = ["uv", "pip", "install", "--upgrade", "--no-cache", "--quiet", repo_url]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode != 0:
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade",
                       "--no-cache-dir", "--quiet", repo_url]
                subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except Exception:
            pass

        _save_cache(latest_sha, updated=True)
    else:
        # No update needed, just refresh timestamp
        _save_cache(latest_sha or current_sha, updated=False)


def auto_update(quiet: bool = False) -> bool:
    """
    Spawns a non-blocking background thread to check and update AlpieCode.
    Adds zero latency to CLI startup (< 10ms).

    Also prints a one-time notice if a previous update was installed.
    """
    if os.environ.get("ALPIECODE_NO_UPDATE") == "1":
        return False

    # Show notice if last run installed an update
    if not quiet:
        _check_pending_update_notice()

    # Check cache interval — don't spam GitHub API
    cache = _get_cache()
    last_check = cache.get("timestamp", 0)
    if time.time() - last_check < CHECK_INTERVAL_SECONDS:
        return False

    # Launch background thread so startup is INSTANT
    thread = threading.Thread(target=_bg_update_worker, args=(quiet,), daemon=True)
    thread.start()
    return True
