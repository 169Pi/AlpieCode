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

import threading

CACHE_FILE = Path.home() / ".alpiecode" / "update_cache.json"
CHECK_INTERVAL_SECONDS = 86400  # Check at most once per 24 hours in background


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


def _bg_update_worker(quiet: bool = False) -> None:
    """Background worker function that performs the check and upgrade silently."""
    try:
        url = "https://api.github.com/repos/169Pi/AlpieCode/commits/main"
        req = urllib.request.Request(url, headers={"User-Agent": "AlpieCode-Updater"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latest_sha = data.get("sha", "")
    except Exception:
        return

    current_sha = _get_installed_sha()
    if latest_sha and latest_sha != current_sha:
        repo_url = "git+https://github.com/169Pi/AlpieCode.git@main"
        cmd = ["uv", "pip", "install", "--upgrade", "--no-cache", "--quiet", repo_url]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode != 0:
                cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "--no-cache-dir", "--quiet", repo_url]
                subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except Exception:
            pass

    _save_cache(latest_sha or current_sha)


def auto_update(quiet: bool = False) -> bool:
    """
    Spawns a non-blocking background thread to check and update AlpieCode
    without adding any latency to the CLI startup (< 10ms).
    """
    if os.environ.get("ALPIECODE_NO_UPDATE") == "1":
        return False

    # Check cache interval
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text())
            last_check = data.get("timestamp", 0)
            if time.time() - last_check < CHECK_INTERVAL_SECONDS:
                return False
        except Exception:
            pass

    # Launch background thread so startup is INSTANT (< 10ms)
    thread = threading.Thread(target=_bg_update_worker, args=(quiet,), daemon=True)
    thread.start()
    return True
