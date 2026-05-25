"""Provider interface shared by every AI backend."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(Exception):
    """Raised when a provider call fails in a way the worker should record."""

    def __init__(self, message: str, *, retriable: bool = False):
        super().__init__(message)
        self.retriable = retriable


def is_quota_or_rate_limit_error(exc: BaseException) -> bool:
    """True when Gemini (or similar) rejected the call due to quota / rate limits."""
    msg = str(exc).lower()
    return any(
        token in msg
        for token in (
            "429",
            "quota",
            "rate limit",
            "rate_limit",
            "resource_exhausted",
            "exceeded your current quota",
            "too many requests",
        )
    )


@dataclass
class GenerationResult:
    output: str
    provider: str


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, prompt: str, *, context: str = "") -> GenerationResult: ...
