"""
Agent orchestrator for AlpieCode.

Coordinates inference backends, context management, prompt construction, and tool execution.
Yields a stream of transport-agnostic AgentEvent objects.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from .backends.base import ChatResponse, InferenceBackend, ToolCall
from .backends.local_backend import LocalBackend
from .backends.openai_backend import OpenAIBackend
from .config import Config, is_server_reachable
from .context import ContextManager
from .executor import ToolExecutor, ToolResult
from .memory import extract_and_save_memories
from .prompt import PromptBuilder, is_simple_task
from .session import Session, SessionManager


@dataclass
class AgentEvent:
    """Structured event yielded by the orchestrator."""
    type: str
    data: Dict[str, Any]


def resolve_backend(cfg: Config, timeout: float = 2.0) -> InferenceBackend:
    """Resolve online vs offline backend based on server reachability.

    Uses a generous timeout at startup (2s default) to avoid false negatives
    when the remote API is slow to respond (e.g. Azure VM cold start).
    """
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
    ) -> Iterator[AgentEvent]:
        """
        Run full agent task loop for a session. Yields AgentEvents.
        """
        # Dynamic backend re-check: if currently on LocalBackend but remote
        # API is now reachable, switch to OnlineBackend automatically.
        # This handles the case where the server started offline but the
        # remote API came online later (e.g. VM cold start, network hiccup).
        if isinstance(self.backend, LocalBackend) and is_server_reachable(cfg.base_url, timeout=1.5):
            self.backend = OpenAIBackend(cfg)

        is_offline = not self.backend.is_available or isinstance(self.backend, LocalBackend)
        session.is_offline = is_offline

        # Configure tools & system prompt
        active_tools = self.prompt_builder.get_tools(is_offline=is_offline)
        system_prompt = self.prompt_builder.build_system_prompt(session.workdir, is_offline=is_offline)
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
        })

        # Adaptive thinking check
        enable_thinking = cfg.enable_thinking
        if enable_thinking and is_simple_task(task):
            enable_thinking = False
            yield AgentEvent("adaptive_mode", {"message": "Simple task detected, skipping deep reasoning."})

        for turn in range(cfg.max_turns):
            if session.cancelled:
                yield AgentEvent("cancelled", {"turn": turn + 1})
                break

            # Context compaction check
            if session.context.check_and_compact():
                yield AgentEvent("compaction", {"turn": turn + 1})

            yield AgentEvent("turn_start", {"turn": turn + 1})

            try:
                max_tokens = 2048 if is_offline else cfg.max_tokens
                resp = self.backend.chat_completion(
                    messages=session.context.messages,
                    tools=active_tools,
                    temperature=cfg.temperature,
                    max_tokens=max_tokens,
                    enable_thinking=enable_thinking,
                )
            except Exception as e:
                # Online error auto-fallback attempt
                if not is_offline and isinstance(self.backend, OpenAIBackend):
                    yield AgentEvent("fallback", {"error": str(e), "message": "Falling back to local engine"})
                    self.backend = LocalBackend(cfg)
                    session.is_offline = True
                    is_offline = True
                    active_tools = self.prompt_builder.get_tools(is_offline=True)
                    try:
                        resp = self.backend.chat_completion(
                            messages=session.context.messages,
                            tools=active_tools,
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

            # Extract tool calls
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

            # Assistant text response
            if resp.content:
                yield AgentEvent("message", {"content": resp.content})
                extract_and_save_memories(session.workdir, session.context.messages)
                yield AgentEvent("done", {"summary": resp.content})
                return

            # Exhausted tokens or empty response
            extract_and_save_memories(session.workdir, session.context.messages)
            yield AgentEvent("done", {"summary": "Task completed."})
            return

        yield AgentEvent("max_turns_reached", {"max_turns": cfg.max_turns})
        extract_and_save_memories(session.workdir, session.context.messages)
