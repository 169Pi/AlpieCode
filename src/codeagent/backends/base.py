"""
Inference backend interface for AlpieCode.

Defines the contract (Protocol) and dataclasses for all inference providers
(OpenAI-compatible server, local GGUF model, etc.).
"""

from dataclasses import dataclass
from typing import Any, List, Optional, Protocol, runtime_checkable


@dataclass
class ToolCall:
    """Normalized tool call representation."""
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResponse:
    """Normalized inference response structure."""
    content: Optional[str]
    reasoning: Optional[str]
    tool_calls: Optional[List[ToolCall]]
    raw: Any = None


@runtime_checkable
class InferenceBackend(Protocol):
    """Contract that all inference backends must implement."""

    @property
    def name(self) -> str:
        """Human-readable backend name."""
        ...

    @property
    def is_available(self) -> bool:
        """Whether the backend is available/reachable."""
        ...

    @property
    def context_window(self) -> int:
        """Maximum context window in tokens."""
        ...

    def chat_completion(
        self,
        messages: List[dict],
        tools: Optional[List[dict]] = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        enable_thinking: bool = True,
    ) -> ChatResponse:
        """Execute chat completion and return a normalized ChatResponse."""
        ...

    def shutdown(self) -> None:
        """Clean up resources."""
        ...
