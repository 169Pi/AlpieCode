"""
Prompt rephraser service for AlpieCode.

Internally solidifies raw user prompts into high-grade software engineering
specifications before agent execution begins. Operates silently behind the scenes.
"""

import logging
import re
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

REPHRASER_SYSTEM_PROMPT = """\
You are an expert AI prompt engineer and principal software architect.
Your job is to transform the user's raw prompt into a clear, solid, and unambiguous software engineering specification.

Guidelines:
1. If the prompt is a simple Q&A, greeting, or direct conceptual question (e.g. "what is X?", "explain Y", "hi", "how does Z work"):
   - Keep it clean, direct, and concise. Do NOT add unnecessary software development boilerplate.
2. If the prompt is a coding, debugging, refactoring, testing, or feature creation task:
   - Expand it into a solid, structured engineering prompt with:
     * Objective: Explicit statement of what needs to be created, modified, or fixed
     * Scope & Architecture: Target files, patterns, and module structure
     * Technical Requirements: Key functionality, edge cases, error handling
     * Quality & Implementation: Complete, production-ready code on Turn 1 with no stubs, placeholders, or missing imports
     * Verification Criteria: Specific commands or tests to run to verify that the implementation works
3. Output ONLY the refined prompt text. Do NOT include greetings, conversational remarks, thinking blocks, or preambles like "Here is the refined prompt:".
"""


def _clean_rephrased_text(text: str) -> str:
    """Clean model output to extract only the actual refined specification."""
    if not text:
        return ""

    cleaned = text.strip()

    # 1. Remove <think>...</think> if present
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL).strip()

    # 2. Remove "Thinking Process: ... \n\n" if model output chain-of-thought
    if "thinking process:" in cleaned.lower():
        # Look for double newline or start of markdown header after thinking process
        match = re.search(r"(?:thinking process:.*?\n\n|\bobjective\b|\bscope\b)", cleaned, flags=re.DOTALL | re.IGNORECASE)
        if match:
            # If matched starting with objective/scope, slice from there
            obj_match = re.search(r"(\*\*objective\*\*|objective:|#\s+objective|\*\*goal\*\*)", cleaned, flags=re.IGNORECASE)
            if obj_match:
                cleaned = cleaned[obj_match.start():].strip()

    # 3. Clean any leading conversational fluff
    fluff_prefixes = [
        "here is the refined prompt:",
        "here is the solidified prompt:",
        "refined prompt:",
        "solidified prompt:",
        "here is a solid prompt:",
        "here is the specification:",
        "refined specification:",
    ]
    for prefix in fluff_prefixes:
        if cleaned.lower().startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
            break

    # 4. Strip outer code fences if accidentally wrapped
    if cleaned.startswith("```") and cleaned.endswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()

    return cleaned.strip()


class PromptRephraser:
    """Refines and solidifies tasks into rigorous engineering specifications."""

    def __init__(self, system_prompt: str = REPHRASER_SYSTEM_PROMPT):
        self.system_prompt = system_prompt

    def rephrase(
        self,
        task: str,
        backend: Any,
        task_context: Optional[Any] = None,
        timeout: float = 6.0,
    ) -> str:
        """Solidify user task into a high-grade prompt internally.

        Fails open: returns original task if rephrasing fails, times out,
        or if backend is unavailable.
        """
        if not task or not task.strip():
            return task

        # If pure trivial greeting, skip model call for instant response
        clean_task = task.strip().lower()
        if clean_task in ("hi", "hello", "hey", "help", "ping", "exit", "quit"):
            return task

        # Check if backend is available
        if backend is None or not getattr(backend, "is_available", True):
            return task

        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"User Task:\n{task.strip()}"},
            ]

            # Invoke backend with enable_thinking=False for ultra-fast, deterministic response
            kwargs = {
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": 1024,
            }
            try:
                response = backend.chat_completion(**kwargs, enable_thinking=False)
            except TypeError:
                response = backend.chat_completion(**kwargs)

            refined = ""
            if hasattr(response, "content") and response.content:
                refined = response.content.strip()
            elif isinstance(response, dict):
                refined = response.get("content", "").strip()

            if not refined:
                return task

            cleaned = _clean_rephrased_text(refined)
            return cleaned if cleaned else task

        except Exception as e:
            logger.debug(f"Prompt rephrasing skipped due to exception: {e}")
            return task
