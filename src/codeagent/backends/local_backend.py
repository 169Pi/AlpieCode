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

    def chat_completion(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        enable_thinking: bool = True,
    ) -> ChatResponse:
        model = self._ensure_model()
        resp = model.create_chat_completion(
            messages=messages,
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
