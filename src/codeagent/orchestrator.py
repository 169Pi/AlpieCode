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
from .config import Config, is_server_reachable
from .memory import extract_and_save_memories
from .discovery import build_task_context, COMPLEXITY_CONFIG
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
        complexity = task_context.complexity

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

        # ── Determine effective max_turns and max_tokens ──
        effective_max_turns = task_context.max_turns
        effective_max_tokens = task_context.max_tokens

        # User override: if they set --max-turns explicitly, respect it
        if getattr(cfg, "_explicit_max_turns", False):
            effective_max_turns = cfg.max_turns

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

        # ── Dynamic backend re-check ──
        if isinstance(self.backend, LocalBackend) and is_server_reachable(cfg.base_url, timeout=1.5):
            self.backend = OpenAIBackend(cfg)

        is_offline = not self.backend.is_available or isinstance(self.backend, LocalBackend)
        session.is_offline = is_offline

        # ── Configure tools & system prompt based on complexity ──
        active_tools = self.prompt_builder.get_tools(is_offline=is_offline, complexity=complexity)
        system_prompt = self.prompt_builder.build_system_prompt(
            session.workdir, is_offline=is_offline, complexity=complexity,
            task_context=task_context,
        )
        session.context.set_system_prompt(system_prompt)

        user_content = self.prompt_builder.build_user_content(
            task=task,
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
            "backend": self.backend.name,
            "is_offline": is_offline,
            "tool_count": len(active_tools),
            "complexity": complexity,
        })

        if complexity in ("medium", "high"):
            session.context.add_user_message(
                f"[BUDGET & GOAL] Available turn budget: {effective_max_turns} turns. "
                "Plan the needed components, create the complete files, verify with bash, "
                "and finish with DONE: <summary> as soon as verification succeeds."
            )

        # ── Adaptive thinking ──
        enable_thinking = cfg.enable_thinking or task_context.enable_thinking
        if enable_thinking and complexity in ("qa", "low"):
            enable_thinking = False
            yield AgentEvent("adaptive_mode", {"message": "Simple task detected, skipping deep reasoning."})

        # ── Turn loop ──
        wrap_up_injected = False

        for turn in range(effective_max_turns):
            if session.cancelled:
                yield AgentEvent("cancelled", {"turn": turn + 1})
                break

            # Context compaction
            if session.context.check_and_compact():
                yield AgentEvent("compaction", {"turn": turn + 1})

            # ── Progressive wrap-up injection ──
            # Step 1: Gentle verification reminder at 70%
            if not wrap_up_injected and turn >= int(effective_max_turns * 0.70):
                wrap_up_injected = True
                remaining = effective_max_turns - turn
                session.context.add_user_message(
                    f"[SYSTEM] Turn budget update: {remaining} turns remaining. "
                    "Ensure all necessary files are created and run verification tests now. "
                    "As soon as verification succeeds, output DONE: <summary>."
                )
                yield AgentEvent("wrap_up", {"turn": turn + 1, "remaining": remaining})

            # Step 2: Final wrap-up call at 90%
            if not getattr(self, "_final_wrap_up_injected", False) and turn >= int(effective_max_turns * 0.90):
                self._final_wrap_up_injected = True
                remaining = effective_max_turns - turn
                session.context.add_user_message(
                    f"[SYSTEM] FINAL TURNS: Only {remaining} turns remaining. "
                    "Do not start new exploration. Fix any remaining errors and output DONE: <summary>."
                )

            yield AgentEvent("turn_start", {"turn": turn + 1})

            try:
                if enable_thinking:
                    max_tokens = 4096 if is_offline else max(effective_max_tokens, 16384)
                else:
                    max_tokens = 2048 if is_offline else effective_max_tokens

                resp = self.backend.chat_completion(
                    messages=session.context.messages,
                    tools=active_tools if active_tools else None,
                    temperature=cfg.temperature,
                    max_tokens=max_tokens,
                    enable_thinking=enable_thinking,
                )
            except Exception as e:
                # Online error -> fallback to local
                if not is_offline and isinstance(self.backend, OpenAIBackend):
                    yield AgentEvent("fallback", {"error": str(e), "message": "Falling back to local engine"})
                    self.backend = LocalBackend(cfg)
                    session.is_offline = True
                    is_offline = True
                    active_tools = self.prompt_builder.get_tools(is_offline=True, complexity=complexity)
                    try:
                        resp = self.backend.chat_completion(
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
                    yield AgentEvent("error", {"error": str(e)})
                    return

            if resp.reasoning:
                yield AgentEvent("thinking", {"content": resp.reasoning})

            session.context.add_assistant_response(resp)

            # ── DONE detection in assistant content ──
            if resp.content and "DONE:" in resp.content.upper():
                # Model said DONE — finish even if there are tool calls
                tool_calls = session.executor.extract_tool_calls(resp)
                if tool_calls:
                    # Execute final tool calls before finishing
                    results = session.executor.execute_tool_calls(tool_calls)
                    for res in results:
                        yield AgentEvent("tool_result", {
                            "turn": turn + 1,
                            "id": res.tool_call_id,
                            "name": res.name,
                            "content": res.content,
                            "duration_ms": res.duration_ms,
                        })
                        session.context.add_tool_result(res.tool_call_id, res.content)

                yield AgentEvent("message", {"content": resp.content})
                extract_and_save_memories(session.workdir, session.context.messages)

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
                        "turn": turn + 1,
                        "id": tc.id,
                        "name": tc.name,
                        "arguments": tc.arguments,
                    })

                results = session.executor.execute_tool_calls(tool_calls)

                for res in results:
                    yield AgentEvent("tool_result", {
                        "turn": turn + 1,
                        "id": res.tool_call_id,
                        "name": res.name,
                        "content": res.content,
                        "duration_ms": res.duration_ms,
                    })
                    session.context.add_tool_result(res.tool_call_id, res.content)

                continue

            # Text-only response = done
            if resp.content:
                if is_cacheable and turn == 0:
                    try:
                        cache = get_cache()
                        cache.put(task, resp.content, reasoning=resp.reasoning)
                    except Exception:
                        pass

                yield AgentEvent("message", {"content": resp.content})
                extract_and_save_memories(session.workdir, session.context.messages)
                yield AgentEvent("done", {"summary": resp.content})
                return

            # Empty response
            extract_and_save_memories(session.workdir, session.context.messages)
            yield AgentEvent("done", {"summary": "Task completed."})
            return

        yield AgentEvent("max_turns_reached", {"max_turns": effective_max_turns})
        extract_and_save_memories(session.workdir, session.context.messages)
