"""
Tool execution service for AlpieCode.

Extracts, parses, and dispatches tool calls from model responses.
Supports parallel execution for read-only tools, sequential execution for mutating tools,
loop guards, and compilation recovery tracking.
"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from .backends.base import ChatResponse, ToolCall
from .tools import make_dispatch

READ_ONLY_TOOLS = frozenset({"read_file", "list_files", "file_search", "fetch_url", "web_search"})


@dataclass
class ToolResult:
    """Result of a tool execution."""
    tool_call_id: str
    name: str
    content: str
    duration_ms: float


def parse_text_tool_calls(text: str) -> List[dict]:
    """
    Ultra-robust parser for tool calls printed in model text.
    Handles XML tag format, JSON format, and loose/unclosed syntax.
    """
    if not text:
        return []

    tool_calls = []

    # 1. Try parsing JSON blocks inside <tool_call> or ```json
    json_matches = re.findall(r"(?:<tool_call>|```json)\s*(\{.*?\})\s*(?:</tool_call>|```|$)", text, re.DOTALL)
    for jm in json_matches:
        try:
            data = json.loads(jm.strip())
            if isinstance(data, dict) and "name" in data:
                tool_calls.append({
                    "name": data["name"],
                    "arguments": data.get("arguments", {})
                })
        except Exception:
            pass

    if tool_calls:
        return tool_calls

    # 2. Parse XML/tag format: <function=NAME>
    fn_matches = list(re.finditer(r"<function=([a-zA-Z0-9_]+)>", text))

    for idx, match in enumerate(fn_matches):
        func_name = match.group(1)
        start_pos = match.end()
        end_pos = fn_matches[idx + 1].start() if idx + 1 < len(fn_matches) else len(text)
        chunk = text[start_pos:end_pos]

        args = {}
        param_matches = list(re.finditer(r"<parameter=([a-zA-Z0-9_]+)>", chunk))

        for p_idx, p_match in enumerate(param_matches):
            key = p_match.group(1)
            p_start = p_match.end()
            p_end = param_matches[p_idx + 1].start() if p_idx + 1 < len(param_matches) else len(chunk)
            val_raw = chunk[p_start:p_end]

            val_clean = re.sub(r"(</parameter>|</function>|</tool_call>).*$", "", val_raw, flags=re.DOTALL).strip()
            args[key] = val_clean

        tool_calls.append({
            "name": func_name,
            "arguments": args
        })

    return tool_calls


class ToolExecutor:
    """Executes tool calls for a workspace."""

    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.dispatch = make_dispatch(workdir)
        self.tool_call_history: List[Tuple[str, str]] = []
        self.compile_fail_counts: Dict[str, int] = {}

    def extract_tool_calls(self, response: ChatResponse) -> List[ToolCall]:
        """Extract tool calls from response (structured or text format)."""
        if response.tool_calls:
            return response.tool_calls

        if response.content and "<tool_call>" in response.content:
            parsed = parse_text_tool_calls(response.content)
            return [
                ToolCall(
                    id=f"text_call_{i+1}",
                    name=tc["name"],
                    arguments=tc["arguments"],
                )
                for i, tc in enumerate(parsed)
            ]
        return []

    def execute_tool_calls(
        self,
        tool_calls: List[ToolCall],
        on_tool_start: Optional[Callable[[str, dict], None]] = None,
        on_tool_end: Optional[Callable[[str, str], None]] = None,
    ) -> List[ToolResult]:
        """Execute a list of tool calls using parallel dispatch for read-only tools."""
        if not tool_calls:
            return []

        all_read_only = all(tc.name in READ_ONLY_TOOLS for tc in tool_calls)
        use_parallel = all_read_only and len(tool_calls) > 1

        results: List[ToolResult] = []

        if use_parallel:
            results_map: Dict[str, Tuple[str, float]] = {}
            with ThreadPoolExecutor(max_workers=min(8, len(tool_calls))) as pool:
                future_to_tc = {}
                for tc in tool_calls:
                    if on_tool_start:
                        on_tool_start(tc.name, tc.arguments)
                    t0 = time.monotonic()
                    fn = self.dispatch.get(tc.name)
                    if fn:
                        future = pool.submit(fn, tc.arguments)
                    else:
                        future = pool.submit(lambda: f"error: Unknown tool '{tc.name}'")
                    future_to_tc[future] = (tc, t0)

                for future in as_completed(future_to_tc):
                    tc, t0 = future_to_tc[future]
                    elapsed = (time.monotonic() - t0) * 1000
                    try:
                        res_str = str(future.result())
                    except Exception as e:
                        res_str = f"error: {e}"
                    results_map[tc.id] = (res_str, elapsed)

            for tc in tool_calls:
                res_str, elapsed = results_map[tc.id]
                if on_tool_end:
                    on_tool_end(tc.name, res_str)
                results.append(ToolResult(tool_call_id=tc.id, name=tc.name, content=res_str, duration_ms=elapsed))
            return results

        # Sequential execution
        for tc in tool_calls:
            if on_tool_start:
                on_tool_start(tc.name, tc.arguments)
            t0 = time.monotonic()
            fn = self.dispatch.get(tc.name)
            if fn:
                try:
                    res_str = str(fn(tc.arguments))
                except Exception as e:
                    res_str = f"error: {e}"
            else:
                res_str = f"error: Unknown tool '{tc.name}'"
            elapsed = (time.monotonic() - t0) * 1000

            # Tool loop detection guard
            call_sig = (tc.name, json.dumps(tc.arguments, sort_keys=True))
            self.tool_call_history.append(call_sig)
            repeat_count = sum(1 for item in self.tool_call_history[-5:] if item == call_sig)

            if repeat_count >= 3:
                res_str += (
                    f"\n\n🛑 REPEATED TOOL CALL LOOP DETECTED (attempt #{repeat_count}). "
                    f"You have already executed '{tc.name}' with these exact parameters {repeat_count} times in a row. "
                    "All checks have passed. Do NOT run this tool again. Output your final summary starting with: DONE: <summary>."
                )

            # Compilation failure recovery hint
            if tc.name == "bash":
                cmd = tc.arguments.get("command", "")
                is_compile = any(kw in cmd for kw in ["g++", "gcc", "clang", "make", "cmake", "cargo build", "rustc"])
                if is_compile and "exit_code" in str(res_str):
                    try:
                        result_data = json.loads(res_str.split("\n", 1)[-1] if res_str.startswith("⚠️") else res_str)
                        if result_data.get("exit_code", 0) != 0:
                            compile_key = cmd.strip()
                            self.compile_fail_counts[compile_key] = self.compile_fail_counts.get(compile_key, 0) + 1
                            if self.compile_fail_counts[compile_key] >= 3:
                                res_str += (
                                    "\n\n🛑 REPEATED COMPILATION FAILURE (attempt "
                                    f"#{self.compile_fail_counts[compile_key]}). "
                                    "STOP making blind edits. Re-read the ENTIRE source file with "
                                    "read_file to understand its full structure, then fix ALL errors "
                                    "comprehensively in one edit."
                                )
                        else:
                            self.compile_fail_counts.pop(cmd.strip(), None)
                    except (json.JSONDecodeError, ValueError):
                        pass

            if on_tool_end:
                on_tool_end(tc.name, res_str)

            results.append(ToolResult(tool_call_id=tc.id, name=tc.name, content=res_str, duration_ms=elapsed))

        return results
