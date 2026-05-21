"""Provider interface shared by every AI backend."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderError(Exception):
    """Raised when a provider call fails in a way the worker should record."""

    def __init__(self, message: str, *, retriable: bool = False):
        super().__init__(message)
        self.retriable = retriable


@dataclass
class GenerationResult:
    output: str
    provider: str


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def generate(self, prompt: str, *, context: str = "") -> GenerationResult: ...
