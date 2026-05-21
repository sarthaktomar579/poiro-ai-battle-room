"""AI provider abstraction.

The room never calls a provider directly. It enqueues a job and the
worker pool calls ``get_provider().generate(prompt)``. This is the seam
that lets us swap Gemini for a deterministic mock in tests/demos.
"""
from __future__ import annotations

from .base import AIProvider, GenerationResult, ProviderError
from .gemini import GeminiProvider
from .mock import MockProvider
from ..config import get_settings


def get_provider() -> AIProvider:
    settings = get_settings()
    if settings.ai_provider == "gemini" and settings.gemini_api_key:
        return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
    # Fall back transparently so the demo never hard-fails.
    return MockProvider()


__all__ = [
    "AIProvider",
    "GenerationResult",
    "ProviderError",
    "GeminiProvider",
    "MockProvider",
    "get_provider",
]
