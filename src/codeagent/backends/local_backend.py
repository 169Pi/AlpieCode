"""
Local GGUF model inference backend.
"""

from typing import Any, List, Optional

from ..config import Config
from ..local_model import LocalModel
from .base import ChatResponse, ToolCall


class LocalBackend:
    """Backend for local GGUF model inference via llama-cpp-python."""

    def __init__(self, cfg: Config):
        self._cfg = cfg
        self._model: Optional[LocalModel] = None

    @property
    def name(self) -> str:
        return f"Local GGUF ({self._cfg.model_repo})"

    @property
    def is_available(self) -> bool:
        return True  # Local model is always available (downloads if missing)

    @property
    def context_window(self) -> int:
        return self._cfg.n_ctx

    def _ensure_model(self) -> LocalModel:
        if self._model is None:
            self._model = LocalModel(
                repo_id=self._cfg.model_repo,
                n_ctx=self._cfg.n_ctx,
                n_gpu_layers=self._cfg.n_gpu_layers,
                token=self._cfg.hf_token,
            )
        return self._model

    def load_model(self) -> None:
        """Explicitly load model into VRAM/RAM (warmup)."""
        model = self._ensure_model()
        model.load()

    @staticmethod
    def _sanitize_messages_for_gguf(messages: List[dict]) -> List[dict]:
        """
        Sanitize OpenAI-format messages for GGUF Jinja2 chat templates.
        Fixes 'Can only get item pairs from a mapping' errors by:
        - Ensuring content is always a string (never None or list)
        - Stripping tool_calls and tool messages (GGUF templates don't support them)
        - Removing tool-related role messages
        """
        sanitized = []
        for msg in messages:
            role = msg.get("role", "")
            # Skip tool result messages entirely — GGUF models don't understand them
            if role == "tool":
                continue

            clean = {"role": role}

            # Ensure content is always a string
            content = msg.get("content")
            if content is None:
                content = ""
            elif isinstance(content, list):
                # Multimodal content (image_url + text blocks) — extract text parts
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = "\n".join(text_parts) if text_parts else ""
            elif not isinstance(content, str):
                content = str(content)

            # For assistant messages with tool_calls, embed tool call info in content text
            if role == "assistant" and msg.get("tool_calls"):
                tc_descriptions = []
                for tc in msg["tool_calls"]:
                    if isinstance(tc, dict):
                        fn = tc.get("function", {})
                        name = fn.get("name", "unknown")
                        args = fn.get("arguments", "{}")
                        tc_descriptions.append(f"[Called tool: {name}({args})]")
                if tc_descriptions:
                    content = (content + "\n" + "\n".join(tc_descriptions)).strip()
                # Do NOT include tool_calls key — GGUF template will crash on it

            clean["content"] = content
            sanitized.append(clean)

        return sanitized

    def chat_completion(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        enable_thinking: bool = True,
    ) -> ChatResponse:
        model = self._ensure_model()
        sanitized_msgs = self._sanitize_messages_for_gguf(messages)
        resp = model.create_chat_completion(
            messages=sanitized_msgs,
            tools=tools,
            tool_choice="auto",
            temperature=temperature,
            max_tokens=max_tokens,
            enable_thinking=enable_thinking,
        )
        msg = resp.choices[0].message

        tool_calls = None
        if msg.tool_calls:
            import json
            tool_calls = []
            for tc in msg.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args or "{}")
                    except Exception:
                        args = {}
                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=args if isinstance(args, dict) else {},
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
        if self._model:
            self._model._llm = None
            self._model = None
