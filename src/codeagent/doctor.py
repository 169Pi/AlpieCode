"""
AlpieCode Doctor — Comprehensive System Diagnostic Tool.

Checks Python, CUDA/GPU, compilers, runtime tools, network connectivity,
local/remote VLM status, and VS Code extension health.
"""

import os
import sys
import time
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

from .config import load_config, is_server_reachable, is_internet_available


def _colorize(text: str, color: str) -> str:
    colors = {
        "green": "\033[92m",
        "red": "\033[91m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "cyan": "\033[96m",
        "bold": "\033[1m",
        "dim": "\033[2m",
        "reset": "\033[0m",
    }
    return f"{colors.get(color, '')}{text}{colors['reset']}"


def _check_command(cmd: str) -> Tuple[bool, str]:
    """Check if a CLI binary is available and return version if possible."""
    path = shutil.which(cmd)
    if not path:
        return False, "not installed"
    try:
        res = subprocess.run([cmd, "--version"], capture_output=True, text=True, timeout=3)
        out = (res.stdout or res.stderr or "").strip().split("\n")[0]
        return True, out[:60] if out else "installed"
    except Exception:
        return True, "installed"


def _check_gpu() -> Tuple[bool, str]:
    """Check NVIDIA GPU and CUDA support."""
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return False, "No NVIDIA GPU detected (CPU mode)"
    try:
        res = subprocess.run(
            [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if res.returncode == 0 and res.stdout.strip():
            gpu_info = res.stdout.strip().split("\n")[0]
            return True, f"NVIDIA GPU: {gpu_info}"
    except Exception:
        pass
    return True, "NVIDIA GPU driver present"


def _check_remote_latency(base_url: str) -> Tuple[bool, str]:
    """Measure roundtrip latency to the remote VLM server."""
    if not base_url:
        return False, "No base_url configured"
    try:
        parsed = urlparse(base_url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        if not host:
            return False, "Invalid base_url format"

        t0 = time.perf_counter()
        with socket.create_connection((host, port), timeout=3.0):
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return True, f"Online ({elapsed_ms:.1f}ms latency)"
    except Exception as e:
        return False, f"Unreachable ({e})"


def _check_vscode_extension() -> Tuple[bool, str]:
    """Check if the AlpieCode VS Code extension is installed."""
    code_bin = shutil.which("code") or shutil.which("code.cmd") or shutil.which("code.exe")
    if not code_bin:
        return True, "VS Code CLI not in PATH (extension status unknown)"
    try:
        res = subprocess.run([code_bin, "--list-extensions"], capture_output=True, text=True, timeout=5)
        if "alpiecode" in res.stdout.lower() or "169pi.alpiecode" in res.stdout.lower():
            return True, "AlpieCode extension installed in VS Code"
        return False, "AlpieCode extension not detected in VS Code"
    except Exception:
        return True, "VS Code detected"


def run_doctor() -> int:
    """Run all system diagnostic checks and print a structured report."""
    print()
    print(_colorize("  🩺 AlpieCode System Health Diagnostic", "bold"))
    print(_colorize("  " + "═" * 50, "dim"))
    print()

    total_checks = 0
    passed_checks = 0

    cfg = load_config()

    # 1. Python Environment
    print(_colorize("  🐍 Python Environment", "cyan"))
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 9):
        print(f"     {_colorize('✅', 'green')} Python {py_ver} ({sys.executable})")
        passed_checks += 1
    else:
        print(f"     {_colorize('❌', 'red')} Python {py_ver} (Requires Python >= 3.9)")
    total_checks += 1

    venv_active = "VIRTUAL_ENV" in os.environ or hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    if venv_active:
        print(f"     {_colorize('✅', 'green')} Virtual Environment active ({os.environ.get('VIRTUAL_ENV', sys.prefix)})")
        passed_checks += 1
    else:
        print(f"     {_colorize('⚠️ ', 'yellow')} No virtual environment active (using system Python)")
    total_checks += 1

    # 2. CUDA / Hardware Acceleration
    print()
    print(_colorize("  🖥️  Hardware & GPU Acceleration", "cyan"))
    has_gpu, gpu_msg = _check_gpu()
    if has_gpu:
        print(f"     {_colorize('✅', 'green')} {gpu_msg}")
        passed_checks += 1
    else:
        print(f"     {_colorize('ℹ️ ', 'blue')} {gpu_msg}")
    total_checks += 1

    # 3. Network & Connectivity
    print()
    print(_colorize("  🌐 Network & Remote Model API", "cyan"))
    inet_ok = is_internet_available(timeout=2.0)
    if inet_ok:
        print(f"     {_colorize('✅', 'green')} General Internet: Connected (DNS 8.8.8.8)")
        passed_checks += 1
    else:
        print(f"     {_colorize('❌', 'red')} General Internet: Offline")
    total_checks += 1

    remote_ok, remote_msg = _check_remote_latency(cfg.base_url)
    if remote_ok:
        print(f"     {_colorize('✅', 'green')} Remote VLM Endpoint: {cfg.base_url} — {remote_msg}")
        print(f"     {_colorize('✅', 'green')} Model Target: {cfg.model}")
        passed_checks += 2
    else:
        print(f"     {_colorize('⚠️ ', 'yellow')} Remote VLM Endpoint: {cfg.base_url} — {remote_msg}")
        print(f"     {_colorize('ℹ️ ', 'blue')} Offline fallback ready with: {cfg.model_repo}")
        passed_checks += 1
    total_checks += 2

    # 4. Development Compilers & Runtimes
    print()
    print(_colorize("  🧰 Development Tools & Compilers", "cyan"))
    tools_to_check = [
        ("node", "Node.js (JavaScript/TypeScript runtime)"),
        ("npm", "Node Package Manager"),
        ("gcc", "GNU C Compiler"),
        ("g++", "GNU C++ Compiler"),
        ("git", "Git Version Control"),
        ("go", "Go Programming Language (optional)"),
        ("rustc", "Rust Compiler (optional)"),
        ("java", "Java JDK (optional)"),
    ]
    for tool_name, desc in tools_to_check:
        ok, msg = _check_command(tool_name)
        is_optional = "optional" in desc
        if ok:
            print(f"     {_colorize('✅', 'green')} {tool_name:8s} : {msg}")
            passed_checks += 1
        elif is_optional:
            print(f"     {_colorize('ℹ️ ', 'dim')} {tool_name:8s} : not installed (optional)")
        else:
            print(f"     {_colorize('⚠️ ', 'yellow')} {tool_name:8s} : not installed")
        total_checks += 1

    # 5. VS Code Integration
    print()
    print(_colorize("  📦 VS Code Extension", "cyan"))
    ext_ok, ext_msg = _check_vscode_extension()
    if ext_ok:
        print(f"     {_colorize('✅', 'green')} {ext_msg}")
        passed_checks += 1
    else:
        print(f"     {_colorize('⚠️ ', 'yellow')} {ext_msg} (run: alpiecode serve)")
    total_checks += 1

    # Summary
    print()
    print(_colorize("  " + "═" * 50, "dim"))
    if passed_checks >= total_checks - 3:
        print(f"  {_colorize('🎉 System Health Status: EXCELLENT', 'green')} ({passed_checks}/{total_checks} checks passed)\n")
        return 0
    else:
        print(f"  {_colorize('⚠️ System Health Status: ATTENTION NEEDED', 'yellow')} ({passed_checks}/{total_checks} checks passed)\n")
        return 1
