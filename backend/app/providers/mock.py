"""Deterministic-ish mock provider.

Simulates latency, success, failure, and timeouts. Important for the demo
because reviewers may not provide a Gemini key and the assignment
explicitly accepts a clean mock interface.
"""
from __future__ import annotations

import asyncio
import hashlib
import random

from .base import AIProvider, GenerationResult, ProviderError


_TEMPLATES = [
    "Concept: {prompt}\n\nA neon-soaked editorial film opens with a slow dolly across rain-slick "
    "chrome. A model holds the bottle like a talisman; the city blurs behind her as the perfume "
    "ignites a holographic skyline. Tagline: \u201cSmell the future before it remembers you.\u201d",
    "Concept: {prompt}\n\nThree 15s vertical cuts. First: a CRT TV blooms violet smoke that "
    "condenses into the bottle. Second: a barcode tattoo dissolves into a rose. Third: the "
    "tagline appears in glitched kanji and Devanagari. Hashtags: #PoiroDrop #LuxeStatic",
    "Concept: {prompt}\n\nA carousel-style campaign: 6 frames, each shot in a different decade's "
    "look but lit with the same magenta key. A short voiceover loops the line \u201ctime is just "
    "another note in the fragrance pyramid.\u201d Sound design: cassette hiss + 808 sub.",
]


class MockProvider(AIProvider):
    name = "mock"

    def __init__(
        self,
        *,
        min_latency: float = 1.2,
        max_latency: float = 3.0,
        failure_rate: float = 0.08,
        timeout_rate: float = 0.02,
    ):
        self.min_latency = min_latency
        self.max_latency = max_latency
        self.failure_rate = failure_rate
        self.timeout_rate = timeout_rate

    async def generate(self, prompt: str, *, context: str = "") -> GenerationResult:
        # Simulate variable latency
        latency = random.uniform(self.min_latency, self.max_latency)
        await asyncio.sleep(latency)

        roll = random.random()
        if roll < self.timeout_rate:
            # Block long enough for the worker's timeout to fire.
            await asyncio.sleep(60)

        if roll < self.timeout_rate + self.failure_rate:
            raise ProviderError("Mock provider injected transient failure", retriable=True)

        # Deterministic-looking template selection
        idx = int(hashlib.sha256((prompt + context).encode()).hexdigest(), 16) % len(_TEMPLATES)
        body = _TEMPLATES[idx].format(prompt=prompt.strip())
        return GenerationResult(output=body, provider=self.name)
