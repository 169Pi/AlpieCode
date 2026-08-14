"""
OpenAI-compatible API inference backend.
"""

from typing import Any, List, Optional
from openai import OpenAI

from ..config import Config, get_shared_http_client, is_server_reachable
from .base import ChatResponse, ToolCall


class OpenAIBackend:
    """Backend for remote OpenAI-compatible servers (vLLM, Ollama, etc.)."""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._client: Optional[OpenAI] = None

    @property
    def name(self) -> str:
        return f"Online API ({self._cfg.base_url})"

    @property
    def is_available(self) -> bool:
        return is_server_reachable(self._cfg.base_url)

    @property
    def context_window(self) -> int:
        return 262_144

    def _ensure_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=self._cfg.base_url,
                api_key=self._cfg.api_key or "not-needed",
                http_client=get_shared_http_client(),
            )
        return self._client

    def chat_completion(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        enable_thinking: bool = True,
    ) -> ChatResponse:
        client = self._ensure_client()
        params = {
            "model": self._cfg.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "extra_body": {"chat_template_kwargs": {"enable_thinking": enable_thinking}},
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        resp = client.chat.completions.create(**params)
        msg = resp.choices[0].message

        tool_calls = None
        if msg.tool_calls:
            import json
            tool_calls = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except (json.JSONDecodeError, TypeError):
                    args = {}
                # Defensive: ensure args is always a dict (model sometimes returns lists or strings)
                if not isinstance(args, dict):
                    args = {}
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args,
                    )
                )

        reasoning = getattr(msg, "reasoning", None) or getattr(msg, "reasoning_content", None)

        return ChatResponse(
            content=msg.content,
            reasoning=reasoning,
            tool_calls=tool_calls,
            raw=resp,
        )

    def shutdown(self) -> None:
        self._client = None
