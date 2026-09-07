"""
Pre-Commit AST & Syntax Guardrail for AlpieCode.

Validates code syntax before writing to disk, ensuring that corrupt code,
unclosed brackets, indentation errors, or syntax mistakes are caught and
can be self-healed in-place without breaking the user workspace.
"""

import ast
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None


def validate_code_syntax(file_path: str, content: str) -> Tuple[bool, Optional[str]]:
    """
    Validate the syntax of code content for a given file path.
    Returns (is_valid, error_message_if_any).
    """
    if not content or not content.strip():
        return True, None

    ext = Path(file_path).suffix.lower()

    # 1. Python AST Validation
    if ext == ".py":
        try:
            ast.parse(content, filename=file_path)
            return True, None
        except SyntaxError as e:
            line = e.lineno or 0
            col = e.offset or 0
            text_line = e.text.strip() if e.text else ""
            err_msg = (
                f"SyntaxError in '{file_path}' at line {line}, col {col}: {e.msg}.\n"
                f"Offending line: {text_line}\n"
                "Please fix this syntax error."
            )
            return False, err_msg
        except Exception as e:
            return False, f"Syntax parsing error in '{file_path}': {e}"

    # 2. JSON Validation
    if ext == ".json":
        try:
            json.loads(content)
            return True, None
        except Exception as e:
            return False, f"Invalid JSON in '{file_path}': {e}"

    # 3. TOML Validation
    if ext == ".toml" and tomllib:
        try:
            tomllib.loads(content)
            return True, None
        except Exception as e:
            return False, f"Invalid TOML in '{file_path}': {e}"

    # 4. JavaScript / TypeScript Validation
    if ext in (".js", ".mjs", ".cjs"):
        node_bin = shutil.which("node")
        if node_bin:
            try:
                res = subprocess.run(
                    [node_bin, "--check", "-"],
                    input=content,
                    text=True,
                    capture_output=True,
                    timeout=3
                )
                if res.returncode != 0:
                    err = res.stderr.strip() or "Syntax error in JavaScript code"
                    return False, f"JavaScript SyntaxError in '{file_path}': {err}"
            except Exception:
                pass

        # Fallback lexical check for bracket balance
        is_balanced, balance_err = check_bracket_balance(content)
        if not is_balanced:
            return False, f"Syntax issue in '{file_path}': {balance_err}"
        return True, None

    return True, None


def check_bracket_balance(code: str) -> Tuple[bool, Optional[str]]:
    """Fast lexical check for unclosed brackets or strings in code."""
    stack = []
    pairs = {")": "(", "}": "{", "]": "["}
    in_string = False
    quote_char = ""
    escaped = False

    lines = code.split("\n")
    for line_idx, line in enumerate(lines, 1):
        for char_idx, ch in enumerate(line, 1):
            if in_string:
                if escaped:
                    escaped = False
                elif ch == "\\":
                    escaped = True
                elif ch == quote_char:
                    in_string = False
                continue

            if ch in ("'", '"', '`'):
                in_string = True
                quote_char = ch
                continue

            if ch in ("(", "{", "["):
                stack.append((ch, line_idx, char_idx))
            elif ch in (")", "}", "]"):
                if not stack:
                    return False, f"Unexpected closing bracket '{ch}' at line {line_idx}:{char_idx}"
                top, t_line, t_col = stack.pop()
                if pairs[ch] != top:
                    return False, f"Mismatched bracket: opened '{top}' at line {t_line}:{t_col} but closed with '{ch}' at line {line_idx}:{char_idx}"

    if stack:
        top, t_line, t_col = stack[-1]
        return False, f"Unclosed bracket '{top}' opened at line {t_line}:{t_col}"

    return True, None
