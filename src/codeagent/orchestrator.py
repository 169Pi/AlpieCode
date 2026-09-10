def generate_walkthrough_markdown(task: str, summary: str, files: list, commands: list) -> str:
    """Generate Antigravity-style Walkthrough markdown document."""
    lines = [
        f"# Walkthrough: {task}",
        "",
        "## Overview",
        summary.strip() if summary else "All requested changes and verification steps have been completed.",
        "",
        "## Changes Made",
    ]
    if files:
        lines.append("### Modified / Created Files")
        for f in files:
            lines.append(f"- `{f}`")
        lines.append("")
    else:
        lines.append("No files were modified during this session.")
        lines.append("")

    if commands:
        lines.append("## Verification Results")
        for c in commands:
            cmd = c.get("command") or c.get("cmd") or ""
            code = c.get("exit_code", 0)
            status = "✓ Passed" if code == 0 else f"✗ Failed (exit code {code})"
            lines.append(f"- `{cmd}` — **{status}**")
        lines.append("")

    lines.append("## How to Run / Verify")
    lines.append("Review the files above or run your test/build commands to verify project execution.")
    lines.append("")
    return "\n".join(lines)


"""
Agent orchestrator for AlpieCode.

Owns the turn loop, backend resolution, caching, and event stream.
"""

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

from .backends.base import InferenceBackend, ChatResponse
from .backends.local_backend import LocalBackend
from .backends.openai_backend import OpenAIBackend
from .cache import get_cache
from .config import Config, is_server_reachable, is_internet_available
from .memory import extract_and_save_memories
from .discovery import build_task_context, gather_relevant_context, COMPLEXITY_CONFIG
from .progress import ProgressMonitor
from .rephraser import PromptRephraser
from .prompt import PromptBuilder, classify_task
from .session import Session, SessionManager


@dataclass
class AgentEvent:
    type: str
    data: Dict[str, Any]


def resolve_backend(cfg: Config, timeout: float = 2.0) -> InferenceBackend:
    """Resolve online vs offline backend based on server reachability."""
    if is_server_reachable(cfg.base_url, timeout=timeout):
        return OpenAIBackend(cfg)
    return LocalBackend(cfg)


class AgentOrchestrator:
    """Executes agent turn loops and yields AgentEvents."""

    def __init__(
        self,
        backend: InferenceBackend,
        prompt_builder: Optional[PromptBuilder] = None,
    ):
        self.backend = backend
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.rephraser = PromptRephraser()

    def run_task(
        self,
        session: Session,
        task: str,
        cfg: Config,
        image_path: Optional[str] = None,
        video_path: Optional[str] = None,
        url: Optional[str] = None,
        github_repo: Optional[str] = None,
        complexity: Optional[str] = None,
    ) -> Iterator[AgentEvent]:
        """Run full agent task loop. Yields AgentEvents."""

        # ── Phase 0: Discovery — pre-compute task intelligence ──
        task_context = build_task_context(task, session.workdir)
        complexity = complexity or task_context.complexity

        yield AgentEvent("discovery", {
            "intent": task_context.intent,
            "complexity": task_context.complexity,
            "os": task_context.os_name,
            "shell": task_context.shell,
            "project_type": task_context.project_type,
            "frameworks": task_context.frameworks,
            "file_count": task_context.file_count,
        })

        comp_cfg = COMPLEXITY_CONFIG.get(complexity, COMPLEXITY_CONFIG["low"])

        # ── Determine effective max_tokens ──
        effective_max_tokens = task_context.max_tokens

        # Safety ceiling: hard emergency brake (should never be hit naturally)
        safety_ceiling = cfg.max_turns if cfg.max_turns != 200 else 200

        # Track touched files and executed commands for Antigravity Walkthrough
        session_touched_files = set()
        session_executed_commands = []
        verification_nudged = False  # Per-task local flag (prevents cross-session state leak)

        # ── Response cache check ──
        is_cacheable = not any([image_path, video_path, url, github_repo])
        if is_cacheable:
            cache = get_cache()
            cached = cache.get(task)
            if cached:
                yield AgentEvent("start", {
                    "task": task,
                    "workdir": str(session.workdir),
                    "backend": "cache",
                    "is_offline": False,
                    "tool_count": 0,
                    "complexity": complexity,
                })
                yield AgentEvent("cache_hit", {
                    "message": "Returning cached response (instant)",
                })
                if cached.get("reasoning"):
                    yield AgentEvent("thinking", {"content": cached["reasoning"]})
                yield AgentEvent("message", {"content": cached["response"]})
                yield AgentEvent("done", {"summary": cached["response"]})
                return

        # ── Dynamic backend re-check (thread-safe: use task-local backend) ──
        task_backend = self.backend
        if isinstance(task_backend, LocalBackend) and is_server_reachable(cfg.base_url, timeout=1.5):
            task_backend = OpenAIBackend(cfg)

        is_offline = not task_backend.is_available or isinstance(task_backend, LocalBackend)
        session.is_offline = is_offline

        # ── Configure tools & system prompt based on complexity ──
        active_tools = self.prompt_builder.get_tools(is_offline=is_offline, complexity=complexity, task_context=task_context)
        system_prompt = self.prompt_builder.build_system_prompt(
            session.workdir, is_offline=is_offline, complexity=complexity,
            task_context=task_context,
        )
        session.context.set_system_prompt(system_prompt)
        # ── Phase 0.5: Internal Prompt Rephraser (first step, internal only) ──
        yield AgentEvent("status", {
            "phase": "rephrasing",
            "message": "Solidifying task requirements...",
            "task": task,
        })
        rephrased_task = task
        try:
            rephrased_task = self.rephraser.rephrase(task, task_backend, task_context)
        except Exception:
            rephrased_task = task

        yield AgentEvent("status", {
            "phase": "building",
            "message": "Starting build...",
            "rephrased": rephrased_task,
        })

        # ── Phase 0.7: Pre-Read Context Injection ──
        pre_read_ctx = None
        try:
            pre_read_ctx = gather_relevant_context(task, session.workdir, task_context)
        except Exception:
            pass  # Fail open -- never block the agent

        # Append pre-read context to the rephrased task so the agent sees it
        effective_task = rephrased_task
        if pre_read_ctx:
            effective_task = rephrased_task + "\n\n" + pre_read_ctx

        user_content = self.prompt_builder.build_user_content(
            task=effective_task,
            image_path=image_path,
            video_path=video_path,
            url=url,
            workdir=session.workdir,
            github_repo=github_repo,
        )
        session.context.add_user_message(user_content)

        yield AgentEvent("start", {
            "task": task,
            "workdir": str(session.workdir),
            "backend": task_backend.name,
            "is_offline": is_offline,
            "tool_count": len(active_tools),
            "complexity": complexity,
            "rephrased_task": rephrased_task,
        })



        # ── Adaptive thinking ──
        if cfg.enable_thinking:
            enable_thinking = True
        elif complexity in ("qa", "low", "no-thinking"):
            enable_thinking = False
            yield AgentEvent("adaptive_mode", {"message": "No-thinking mode or simple task, skipping reasoning trace."})
        else:
            enable_thinking = task_context.enable_thinking

        # ── Goal-driven turn loop (no fixed limit) ──
        progress_monitor = ProgressMonitor()
        turn = 0

        while True:
            turn += 1

            if session.cancelled:
                yield AgentEvent("cancelled", {"turn": turn})
                break

            # Context compaction
            if session.context.check_and_compact():
                yield AgentEvent("compaction", {"turn": turn})

            # ── Stall Detection & Corrective Intervention ──
            if progress_monitor.is_stalled(threshold=3):
                advice = progress_monitor.get_stall_advice()
                session.context.add_user_message(advice)
                yield AgentEvent("stall_intervention", {
                    "turn": turn,
                    "consecutive_stalls": progress_monitor.consecutive_stalls,
                    "interventions": progress_monitor.stall_interventions,
                })
                # After 3 interventions (= 9+ stalled turns), force wrap-up
                if progress_monitor.stall_interventions >= 3:
                    session.context.add_user_message(
                        "[SYSTEM] Multiple stall interventions have not resolved the issue. "
                        "Finish now with whatever you have. Output DONE: <summary of what was completed>."
                    )

            # ── Safety ceiling (emergency only) ──
            if turn > safety_ceiling:
                yield AgentEvent("safety_ceiling", {"turn": turn, "ceiling": safety_ceiling})
                break

            yield AgentEvent("turn_start", {"turn": turn})

            try:
                if enable_thinking:
                    max_tokens = 4096 if is_offline else max(effective_max_tokens, 16384)
                else:
                    max_tokens = 2048 if is_offline else effective_max_tokens

                if hasattr(task_backend, "chat_completion_stream") and not is_offline:
                    resp = None
                    for event_type, data in task_backend.chat_completion_stream(
                        messages=session.context.messages,
                        tools=active_tools if active_tools else None,
                        temperature=cfg.temperature,
                        max_tokens=max_tokens,
                        enable_thinking=enable_thinking,
                    ):
                        if event_type == "done":
                            resp = data
                        else:
                            yield AgentEvent(event_type, data)
                else:
                    resp = task_backend.chat_completion(
                        messages=session.context.messages,
                        tools=active_tools if active_tools else None,
                        temperature=cfg.temperature,
                        max_tokens=max_tokens,
                        enable_thinking=enable_thinking,
                    )
            except Exception as e:
                # Online error -> only fallback to local GGUF if internet is genuinely unavailable.
                # Server timeouts (read timeout, slow inference) should NOT trigger GGUF fallback
                # because the server IS reachable — it's just slow.
                if not is_offline and isinstance(task_backend, OpenAIBackend):
                    err_str = str(e).lower()
                    is_timeout = "timeout" in err_str or "timed out" in err_str or "read operation timed out" in err_str
                    is_network_down = not is_internet_available(timeout=1.5)

                    if is_timeout and not is_network_down:
                        # Server is alive but slow — retry, don't fallback to GGUF
                        yield AgentEvent("warning", {
                            "message": f"Server inference timed out: {e}. Retrying...",
                        })
                        try:
                            resp = task_backend.chat_completion(
                                messages=session.context.messages,
                                tools=active_tools if active_tools else None,
                                temperature=cfg.temperature,
                                max_tokens=max_tokens,
                                enable_thinking=enable_thinking,
                            )
                        except Exception as retry_err:
                            yield AgentEvent("error", {
                                "error": f"Server inference failed after retry: {retry_err}. "
                                         "The server may be under heavy load. Please try again."
                            })
                            return
                    elif is_network_down:
                        # Internet genuinely unavailable — fallback to local GGUF
                        yield AgentEvent("fallback", {"error": str(e), "message": "Internet unavailable. Falling back to local engine"})
                        task_backend = LocalBackend(cfg)
                        session.is_offline = True
                        is_offline = True
                        active_tools = self.prompt_builder.get_tools(is_offline=True, complexity=complexity)
                        try:
                            resp = task_backend.chat_completion(
                                messages=session.context.messages,
                                tools=active_tools if active_tools else None,
                                temperature=cfg.temperature,
                                max_tokens=2048,
                                enable_thinking=enable_thinking,
                            )
                        except Exception as fallback_err:
                            yield AgentEvent("error", {"error": str(fallback_err)})
                            return
                    else:
                        # Other API error (400, 500, etc.) — report directly, don't fallback
                        yield AgentEvent("error", {"error": f"Server error: {e}"})
                        return
                else:
                    yield AgentEvent("error", {"error": str(e)})
                    return

            if resp is None:
                yield AgentEvent("error", {"error": "Backend returned no response"})
                return

            if resp.reasoning and not (hasattr(task_backend, "chat_completion_stream") and not is_offline):
                yield AgentEvent("thinking", {"content": resp.reasoning})

            session.context.add_assistant_response(resp)

            # Normalize content and reasoning: rescue any DONE: or answer trapped in reasoning
            if (not resp.content or not resp.content.strip()) and resp.reasoning:
                if "DONE:" in resp.reasoning.upper():
                    idx = resp.reasoning.upper().find("DONE:")
                    resp.content = resp.reasoning[idx:].strip()
                    resp.reasoning = resp.reasoning[:idx].strip() or None
                elif "</think>" in resp.reasoning:
                    parts = resp.reasoning.split("</think>", 1)
                    resp.reasoning = parts[0].strip() or None
                    resp.content = parts[1].strip()
                elif any(m in resp.reasoning for m in ["The codebase is complete", "All JavaScript files", "I have implemented", "Verified the"]):
                    resp.content = resp.reasoning.strip()
                    resp.reasoning = None

            # ── DONE detection in assistant content ──
            if resp.content and "DONE:" in resp.content.upper():
                # Model said DONE — finish even if there are tool calls
                tool_calls = session.executor.extract_tool_calls(resp)
                if tool_calls:
                    # Execute final tool calls before finishing
                    results = session.executor.execute_tool_calls(tool_calls)
                    for res in results:
                        yield AgentEvent("tool_result", {
                            "turn": turn,
                            "id": res.tool_call_id,
                            "name": res.name,
                            "content": res.content,
                            "duration_ms": res.duration_ms,
                        })
                        session.context.add_tool_result(res.tool_call_id, res.content)

                if resp.content:
                    # Clean duplicate DONE: if repeated
                    if resp.content.upper().count("DONE:") > 1:
                        parts = re.split(r"(?i)\bDONE:\s*", resp.content)
                        if len(parts) >= 3 and parts[1].strip() == parts[2].strip():
                            resp.content = parts[0] + "DONE: " + parts[1].strip()

                # Only yield 'message' if tokens were NOT already streamed chunk-by-chunk
                if not (hasattr(task_backend, "chat_completion_stream") and not is_offline):
                    yield AgentEvent("message", {"content": resp.content})

                extract_and_save_memories(session.workdir, getattr(session.context, 'all_messages', session.context.messages))

                # Generate and write real walkthrough.md file to the project workspace
                from pathlib import Path as _Path
                try:
                    w_path = _Path(session.workdir) / "walkthrough.md"
                    w_content = generate_walkthrough_markdown(
                        task=task,
                        summary=resp.content,
                        files=sorted(list(session_touched_files)),
                        commands=session_executed_commands,
                    )
                    w_path.write_text(w_content, encoding="utf-8")
                    session_touched_files.add("walkthrough.md")
                except Exception:
                    pass

                yield AgentEvent("walkthrough", {
                    "path": "walkthrough.md",
                    "summary": resp.content,
                    "files": sorted(list(session_touched_files)),
                    "commands": session_executed_commands,
                })

                # ── Soft Verification Gate ──
                # If files were written/modified but no verification was run, nudge the agent
                has_code_files = any(
                    f.endswith((".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".c", ".cpp"))
                    for f in session_touched_files
                )
                has_successful_verify = any(
                    c.get("exit_code", -1) == 0 for c in session_executed_commands
                )
                if has_code_files and not has_successful_verify and not verification_nudged:
                    verification_nudged = True
                    session.context.add_user_message(
                        "[SYSTEM - VERIFICATION] You created/modified code files but did not run "
                        "any verification command. Please run a quick syntax check or test before finishing. "
                        "Then output DONE: <summary>."
                    )
                    yield AgentEvent("verification_nudge", {
                        "files": sorted(list(session_touched_files)),
                        "message": "Nudging agent to verify before completing",
                    })
                    continue

                # Cache if single-turn
                if is_cacheable and turn == 0:
                    try:
                        cache = get_cache()
                        cache.put(task, resp.content, reasoning=resp.reasoning)
                    except Exception:
                        pass

                yield AgentEvent("done", {"summary": resp.content})
                return

            # Extract and execute tool calls
            tool_calls = session.executor.extract_tool_calls(resp)

            if tool_calls:
                for tc in tool_calls:
                    yield AgentEvent("tool_call", {
                        "turn": turn,
                        "id": tc.id,
                        "name": tc.name,
                        "arguments": tc.arguments,
                    })

                results = session.executor.execute_tool_calls(tool_calls)

                for res in results:
                    yield AgentEvent("tool_result", {
                        "turn": turn,
                        "id": res.tool_call_id,
                        "name": res.name,
                        "content": res.content,
                        "duration_ms": res.duration_ms,
                    })
                    session.context.add_tool_result(res.tool_call_id, res.content)

                # Track touched files and commands for walkthrough
                for tc in tool_calls:
                    if tc.name in ("write_file", "edit_file", "apply_patch"):
                        p = tc.arguments.get("path") or tc.arguments.get("filename")
                        if p:
                            session_touched_files.add(p)
                    elif tc.name == "bash":
                        c = tc.arguments.get("command", "")
                        if c:
                            session_executed_commands.append({"command": c, "exit_code": 0})

                # ── Record progress for stall detection ──
                tc_dicts = [{"name": tc.name, "arguments": tc.arguments} for tc in tool_calls]
                res_dicts = [{"content": res.content, "name": res.name} for res in results]
                snap = progress_monitor.record_turn(turn, tc_dicts, res_dicts)
                yield AgentEvent("turn_progress", {
                    "turn": turn,
                    "had_progress": snap.had_progress,
                    "files_created": list(snap.files_created),
                    "files_modified": list(snap.files_modified),
                    "consecutive_stalls": progress_monitor.consecutive_stalls,
                })

                continue

            # Text-only response = done
            if resp.content:
                if is_cacheable and turn == 0:
                    try:
                        cache = get_cache()
                        cache.put(task, resp.content, reasoning=resp.reasoning)
                    except Exception:
                        pass

                if resp.content:
                    # Clean duplicate DONE: if repeated
                    if resp.content.upper().count("DONE:") > 1:
                        parts = re.split(r"(?i)\bDONE:\s*", resp.content)
                        if len(parts) >= 3 and parts[1].strip() == parts[2].strip():
                            resp.content = parts[0] + "DONE: " + parts[1].strip()

                # Only yield 'message' if tokens were NOT already streamed chunk-by-chunk
                if not (hasattr(task_backend, "chat_completion_stream") and not is_offline):
                    yield AgentEvent("message", {"content": resp.content})

                extract_and_save_memories(session.workdir, getattr(session.context, 'all_messages', session.context.messages))
                yield AgentEvent("done", {"summary": resp.content})
                return

            # Empty response
            extract_and_save_memories(session.workdir, getattr(session.context, 'all_messages', session.context.messages))
            yield AgentEvent("done", {"summary": "Task completed."})
            return

        status = progress_monitor.get_status_summary()
        yield AgentEvent("max_turns_reached", {"max_turns": safety_ceiling, "progress": status})
        extract_and_save_memories(session.workdir, getattr(session.context, 'all_messages', session.context.messages))
