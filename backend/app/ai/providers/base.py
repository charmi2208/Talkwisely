"""
Abstract base classes for all AI providers.

Every concrete provider must implement these interfaces.
This ensures the system is provider-agnostic and can swap
LLM / STT / Embedding backends via configuration alone.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# LLM Provider
# ---------------------------------------------------------------------------

@dataclass
class LLMMessage:
    role: str   # system | user | assistant
    content: str


@dataclass
class LLMResponse:
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    finish_reason: str


class LLMProvider(ABC):
    """Abstract interface for all LLM providers."""

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> LLMResponse:
        """Send a chat completion request and return the response."""
        ...

    @abstractmethod
    async def complete_json(
        self,
        messages: list[LLMMessage],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Send a chat completion request expecting JSON output."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        ...


# ---------------------------------------------------------------------------
# STT (Speech-to-Text) Provider
# ---------------------------------------------------------------------------

@dataclass
class TranscriptWord:
    word: str
    start: float
    end: float
    confidence: float | None = None


@dataclass
class TranscriptSegment:
    speaker: str       # "SPEAKER_00", "SPEAKER_01", etc.
    start: float       # seconds
    end: float
    text: str
    words: list[TranscriptWord] | None = None
    confidence: float | None = None


@dataclass
class TranscriptionResult:
    language: str
    duration: float
    segments: list[TranscriptSegment]
    full_text: str


class SpeechToTextProvider(ABC):
    """Abstract interface for speech-to-text providers."""

    @abstractmethod
    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        diarize: bool = True,
        num_speakers: int | None = None,
    ) -> TranscriptionResult:
        """
        Transcribe an audio file.

        Returns a TranscriptionResult with speaker-diarized segments.
        """
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...


# ---------------------------------------------------------------------------
# Embedding Provider
# ---------------------------------------------------------------------------

class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string, returning a float vector."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, returning a list of float vectors."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        ...

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...
