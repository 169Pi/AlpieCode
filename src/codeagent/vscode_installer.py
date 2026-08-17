"""
VS Code Extension Auto-Installer for AlpieCode.

Detects if VS Code is available, checks if the AlpieCode extension is installed,
and prompts/auto-installs the bundled .vsix if missing.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def get_bundled_vsix_path() -> Path:
    """Return path to bundled .vsix inside the codeagent package."""
    pkg_dir = Path(__file__).parent
    return pkg_dir / "extension" / "alpiecode.vsix"


def find_code_cli() -> Optional[str]:
    """Find the VS Code CLI executable across Windows, WSL, Linux, and macOS."""
    for cmd in ("code", "code.cmd", "code.exe"):
        found = shutil.which(cmd)
        if found:
            return found
            
    # Check common WSL / Windows paths if not found directly in PATH
    wsl_code_paths = [
        "/mnt/c/Users/*/AppData/Local/Programs/Microsoft VS Code/bin/code",
        "/usr/local/bin/code",
        "/usr/bin/code",
    ]
    import glob
    for pattern in wsl_code_paths:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
            
    return None


def is_extension_installed() -> bool:
    """Check if 'alpiecode' extension is already installed in VS Code."""
    code_bin = find_code_cli()
    if not code_bin:
        return False

    try:
        res = subprocess.run(
            [code_bin, "--list-extensions"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        if res.returncode == 0:
            installed = res.stdout.lower()
            return "alpiecode" in installed
    except Exception:
        pass

    return False


def ensure_vscode_extension(auto_confirm: bool = False, quiet: bool = False) -> bool:
    """
    Check if VS Code extension is installed. If missing:
    - Asks user: 'Would you like to install the AlpieCode VS Code extension? [Y/n]'
    - If Yes (or auto_confirm=True): installs bundled .vsix via `code --install-extension`
    - Returns True if installed or successfully installed, False otherwise.
    """
    if is_extension_installed():
        if not quiet:
            print("✅ AlpieCode VS Code extension is installed.")
        return True

    code_bin = find_code_cli()
    if not code_bin:
        if not quiet:
            print("ℹ️ VS Code CLI ('code') not detected on PATH. Skipping extension check.")
        return False

    vsix_path = get_bundled_vsix_path()
    if not vsix_path.exists():
        if not quiet:
            print(f"ℹ️ Bundled extension VSIX not found at {vsix_path}")
        return False

    if not quiet:
        print("\n💡 VS Code detected, but the AlpieCode extension is not installed.")

    if not auto_confirm:
        try:
            prompt_text = "   Would you like to install the AlpieCode VS Code extension now? [Y/n]: "
            choice = input(prompt_text).strip().lower()
            if choice and choice not in ("y", "yes"):
                if not quiet:
                    print("   Skipped VS Code extension installation.\n")
                return False
        except (KeyboardInterrupt, EOFError):
            print()
            return False

    print(f"📦 Installing AlpieCode VS Code extension ({vsix_path.name})...")
    try:
        target_arg = str(vsix_path)
        # If running in WSL and code_bin points to Windows binary, convert path to Windows format
        if os.path.exists("/proc/version") and shutil.which("wslpath") and ("/mnt/" in code_bin or code_bin.endswith(".cmd") or code_bin.endswith(".exe")):
            try:
                win_path = subprocess.check_output(["wslpath", "-w", str(vsix_path)], text=True).strip()
                if win_path:
                    target_arg = win_path
            except Exception:
                pass

        res = subprocess.run(
            [code_bin, "--install-extension", target_arg, "--force"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if res.returncode == 0:
            print("✅ AlpieCode VS Code extension installed successfully!")
            print("   👉 Reload VS Code (`Ctrl+Shift+P` → `Developer: Reload Window`) to start chatting!\n")
            return True
        else:
            print(f"⚠️ Could not install VS Code extension: {res.stderr.strip()}\n")
    except Exception as e:
        print(f"⚠️ Extension installation error: {e}\n")

    return False
