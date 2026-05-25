"""Google Gemini provider.

The SDK is synchronous so we run it on a worker thread to keep the event
loop responsive. We classify a small set of errors as ``retriable`` so the
job worker can do bounded exponential backoff.
"""
from __future__ import annotations

import asyncio
from typing import Optional

from ..config import get_settings
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


# Older defaults (e.g. gemini-1.5-flash) return 404 for many API keys now.
_FALLBACK_MODELS = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-2.0-flash-lite",
)


def _normalize_model_name(model: str) -> str:
    """Accept ``gemini-2.5-flash`` or ``models/gemini-2.5-flash``."""
    m = (model or "").strip()
    if m.startswith("models/"):
        m = m[len("models/") :]
    return m or _FALLBACK_MODELS[0]


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        if genai is None:
            raise ProviderError("google-generativeai is not installed")
        if not api_key:
            raise ProviderError("GEMINI_API_KEY is empty")
        genai.configure(api_key=api_key)
        self._api_key = api_key
        settings = get_settings()
        self._model_name = _normalize_model_name(model)
        self._models_to_try = self._build_model_chain(
            self._model_name,
            max_attempts=settings.gemini_max_model_attempts,
        )

    @staticmethod
    def _build_model_chain(primary: str, *, max_attempts: int) -> list[str]:
        """At most ``max_attempts`` model IDs — avoids 5+ API calls per submission."""
        cap = max(1, max_attempts)
        chain = [primary]
        for m in _FALLBACK_MODELS:
            if len(chain) >= cap:
                break
            if m not in chain:
                chain.append(m)
        return chain[:cap]

    async def generate(self, prompt: str, *, context: str = "") -> GenerationResult:
        full_prompt = (
            f"{_SYSTEM_PRIMER}\n\n"
            f"BATTLE BRIEF (from host):\n{context or '(none provided)'}\n\n"
            f"PARTICIPANT SUBMISSION:\n{prompt}\n\n"
            "Respond with the campaign concept only."
        )

        def _call() -> tuple[str, str]:
            last_err: Optional[Exception] = None
            for model_id in self._models_to_try:
                try:
                    model = genai.GenerativeModel(model_id)
                    resp = model.generate_content(full_prompt)
                    text: Optional[str] = getattr(resp, "text", None)
                    if not text:
                        raise ProviderError(
                            "Gemini returned an empty response", retriable=False
                        )
                    return text.strip(), model_id
                except ProviderError:
                    raise
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    msg = str(e).lower()
                    # Try the next model when this ID is unavailable.
                    if "404" in msg or "not found" in msg or "not supported" in msg:
                        continue
                    from .base import is_quota_or_rate_limit_error

                    if is_quota_or_rate_limit_error(e):
                        raise ProviderError(
                            f"Gemini error: {e}", retriable=False
                        ) from e
                    retriable = any(
                        t in msg
                        for t in ("timeout", "unavailable", "503", "temporarily")
                    )
                    raise ProviderError(f"Gemini error: {e}", retriable=retriable) from e

            raise ProviderError(
                f"Gemini error: no working model in {self._models_to_try}. Last: {last_err}",
                retriable=False,
            ) from last_err

        text, used_model = await asyncio.to_thread(_call)
        return GenerationResult(output=text, provider=f"gemini:{used_model}")
