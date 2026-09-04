"""
OpenAI-compatible API inference backend with smart model resolution.
"""

from typing import Any, List, Optional
from openai import OpenAI, NotFoundError

from ..config import Config, get_shared_http_client, is_server_reachable
from .base import ChatResponse, ToolCall


class OpenAIBackend:
    """Backend for remote OpenAI-compatible servers (vLLM, Ollama, etc.)."""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._client: Optional[OpenAI] = None
        self._resolved_model: Optional[str] = None

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

    def _get_available_model(self, client: OpenAI) -> str:
        """Auto-discover the served model name from /v1/models."""
        if self._resolved_model:
            return self._resolved_model
        try:
            models_list = client.models.list()
            if models_list.data:
                for m in models_list.data:
                    if m.id == self._cfg.model or getattr(m, "root", None) == self._cfg.model:
                        self._resolved_model = m.id
                        return self._resolved_model
                self._resolved_model = models_list.data[0].id
                return self._resolved_model
        except Exception:
            pass
        return self._cfg.model

    def chat_completion(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        enable_thinking: bool = True,
    ) -> ChatResponse:
        temp = temperature if temperature is not None else getattr(self._cfg, "temperature", 0.1)
        m_tokens = max_tokens if max_tokens is not None else getattr(self._cfg, "max_tokens", 8192)

        client = self._ensure_client()
        model_name = self._get_available_model(client)

        params = {
            "model": model_name,
            "messages": messages,
            "temperature": temp,
            "max_tokens": m_tokens,
            "extra_body": {"chat_template_kwargs": {"enable_thinking": enable_thinking}},
        }
        if tools:
            params["tools"] = tools
            params["tool_choice"] = "auto"

        try:
            resp = client.chat.completions.create(**params)
        except NotFoundError:
            # Model name mismatch -> re-discover model
            self._resolved_model = None
            model_name = self._get_available_model(client)
            params["model"] = model_name
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
        content = msg.content or ""

        # Extract embedded thinking/reasoning if not provided in separate fields
        if not reasoning and content:
            import re
            if "</think>" in content:
                # Handled when model starts thinking implicitly or with <think>
                parts = content.split("</think>", 1)
                reasoning = parts[0].replace("<think>", "").strip()
                content = parts[1].strip()
            elif "<think>" in content:
                think_match = re.search(r"<think>(.*?)</think>", content, flags=re.DOTALL)
                if think_match:
                    reasoning = think_match.group(1).strip()
                    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
            elif content.strip().lower().startswith("thinking process:") or "\nthinking process:" in content.lower():
                if tool_calls:
                    reasoning = re.sub(r"(?i)^thinking process:\s*", "", content).strip()
                    content = ""
                else:
                    code_match = re.search(r"\n(?=```|Here is|Below is|I will|The following|DONE:|#!/usr|/\*|package\s|import\s[a-z]|from\s[a-z])", content, flags=re.IGNORECASE)
                    if code_match:
                        think_part = content[:code_match.start()]
                        content_part = content[code_match.start():]
                        reasoning = re.sub(r"(?i)^thinking process:\s*", "", think_part).strip()
                        content = content_part.strip()
                    else:
                        reasoning = re.sub(r"(?i)^thinking process:\s*", "", content).strip()
                        content = ""

        return ChatResponse(
            content=content,
            reasoning=reasoning,
            tool_calls=tool_calls,
            raw=resp,
        )

    def shutdown(self) -> None:
        self._client = None
