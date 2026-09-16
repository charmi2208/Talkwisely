"""
Local Whisper STT Provider.

Uses the openai-whisper Python package to run inference locally.
No API key required. Performance depends on hardware and model size.

Model sizes (tradeoff: speed vs accuracy):
  tiny   — fastest, less accurate
  base   — good balance for development
  small  — better accuracy
  medium — production quality
  large  — best accuracy (requires significant RAM)

Set WHISPER_MODEL in .env to control which model is loaded.
"""

import asyncio
from pathlib import Path

from app.ai.providers.base import (
    SpeechToTextProvider,
    TranscriptSegment,
    TranscriptionResult,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("whisper_stt")


class WhisperLocalProvider(SpeechToTextProvider):
    """Transcription using locally-run OpenAI Whisper."""

    def __init__(self) -> None:
        # Lazy import — whisper is a heavy dependency; only load when needed
        try:
            import whisper  # type: ignore
            self._whisper = whisper
            self._model = whisper.load_model(settings.whisper_model)
            logger.info("Whisper model loaded", model=settings.whisper_model)
        except ImportError as e:
            raise ImportError(
                "openai-whisper is not installed. "
                "Run: pip install openai-whisper  (or set STT_PROVIDER=mock)"
            ) from e

    @property
    def provider_name(self) -> str:
        return "whisper_local"

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        diarize: bool = True,
        num_speakers: int | None = None,
    ) -> TranscriptionResult:
        """
        Run Whisper transcription in a thread pool executor to avoid blocking
        the async event loop during the (potentially long) inference step.
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info("Starting Whisper transcription", file=audio_path, model=settings.whisper_model)

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self._run_whisper(audio_path, language),
        )

        return result

    def _run_whisper(self, audio_path: str, language: str | None) -> TranscriptionResult:
        """Run Whisper synchronously (called in executor thread)."""
        transcribe_kwargs: dict = {
            "verbose": False,
            "word_timestamps": True,
        }
        if language:
            transcribe_kwargs["language"] = language

        raw = self._model.transcribe(audio_path, **transcribe_kwargs)

        detected_language: str = raw.get("language", "en")
        raw_segments = raw.get("segments", [])

        segments: list[TranscriptSegment] = []
        speaker_index = 0

        for i, seg in enumerate(raw_segments):
            # Basic heuristic speaker alternation (real diarization requires pyannote)
            # In a production system, integrate pyannote.audio or WhisperX for diarization
            if i > 0:
                prev_end = raw_segments[i - 1].get("end", 0)
                gap = seg.get("start", 0) - prev_end
                if gap > 1.5:
                    # Significant gap — likely speaker change
                    speaker_index = 1 - speaker_index  # Toggle between 0 and 1

            speaker_label = f"SPEAKER_{speaker_index:02d}"

            segments.append(
                TranscriptSegment(
                    speaker=speaker_label,
                    start=float(seg.get("start", 0)),
                    end=float(seg.get("end", 0)),
                    text=str(seg.get("text", "")).strip(),
                    confidence=None,  # Whisper doesn't expose per-segment confidence in base API
                )
            )

        full_text = raw.get("text", "")
        duration = raw_segments[-1]["end"] if raw_segments else 0.0

        logger.info(
            "Whisper transcription complete",
            language=detected_language,
            segments=len(segments),
            duration=duration,
        )

        return TranscriptionResult(
            language=detected_language,
            duration=float(duration),
            segments=segments,
            full_text=str(full_text),
        )
