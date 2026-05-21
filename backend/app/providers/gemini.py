"""Google Gemini provider.

The SDK is synchronous so we run it on a worker thread to keep the event
loop responsive. We classify a small set of errors as ``retriable`` so the
job worker can do bounded exponential backoff.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from .base import AIProvider, GenerationResult, ProviderError

try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover - import guarded so mock-only demos still run
    genai = None  # type: ignore


_SYSTEM_PRIMER = (
    "You are the creative judge for a live AI battle room. A host has set a brief "
    "and a participant has submitted a creative interpretation. Produce a vivid, "
    "concrete, on-brand campaign concept in 120-180 words. Use short paragraphs. "
    "Do not refuse \u2013 if the brief is risky, soften it but still deliver a "
    "creative answer. End with a single punchy tagline."
)


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        if genai is None:
            raise ProviderError("google-generativeai is not installed")
        if not api_key:
            raise ProviderError("GEMINI_API_KEY is empty")
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self._model_name = model

    async def generate(self, prompt: str, *, context: str = "") -> GenerationResult:
        full_prompt = (
            f"{_SYSTEM_PRIMER}\n\n"
            f"BATTLE BRIEF (from host):\n{context or '(none provided)'}\n\n"
            f"PARTICIPANT SUBMISSION:\n{prompt}\n\n"
            "Respond with the campaign concept only."
        )

        def _call() -> str:
            try:
                resp = self._model.generate_content(full_prompt)
            except Exception as e:  # noqa: BLE001 - SDK raises many distinct types
                msg = str(e).lower()
                retriable = any(t in msg for t in ("rate", "timeout", "unavailable", "503", "429"))
                raise ProviderError(f"Gemini error: {e}", retriable=retriable) from e

            text: Optional[str] = getattr(resp, "text", None)
            if not text:
                # Safety blocks / empty responses fall here.
                raise ProviderError("Gemini returned an empty response", retriable=False)
            return text.strip()

        text = await asyncio.to_thread(_call)
        return GenerationResult(output=text, provider=f"gemini:{self._model_name}")
