"""
Hosted Whisper STT Provider (OpenAI-compatible /audio/transcriptions).

Works with Groq (whisper-large-v3-turbo) or OpenAI (whisper-1). Before upload,
ffmpeg converts the recording to 16 kHz mono MP3, which also extracts audio from
video files and keeps most calls under the provider's upload limit. Longer
recordings are split into 10-minute parts and stitched back together.

Hosted Whisper has no diarization, so speakers are guessed from pauses here and
refined later by the transcript-cleaning agent.
"""

import asyncio
import math
import shutil
import subprocess
import tempfile
from pathlib import Path

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.providers.base import SpeechToTextProvider, TranscriptionResult, TranscriptSegment
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("whisper_api_stt")

UPLOADABLE = {".flac", ".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".ogg", ".wav", ".webm"}
PART_SECONDS = 600
SPEAKER_CHANGE_GAP = 1.2  # seconds of silence that usually means the other person is talking

# verbose_json reports the language by name; the app stores ISO codes
LANGUAGE_CODES = {
    "english": "en", "hindi": "hi", "gujarati": "gu", "marathi": "mr", "spanish": "es",
    "french": "fr", "german": "de", "portuguese": "pt", "italian": "it", "arabic": "ar",
    "japanese": "ja", "chinese": "zh", "tamil": "ta", "telugu": "te", "bengali": "bn",
}


def _field(obj, name, default=None):
    return obj.get(name, default) if isinstance(obj, dict) else getattr(obj, name, default)


class WhisperAPIProvider(SpeechToTextProvider):
    """Transcription through a hosted, OpenAI-compatible Whisper endpoint."""

    def __init__(self) -> None:
        api_key = settings.stt_api_key or settings.llm_api_key
        base_url = settings.stt_base_url or settings.llm_base_url
        if not api_key:
            raise ValueError("STT_PROVIDER=whisper_api needs STT_API_KEY or LLM_API_KEY")
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = settings.stt_api_model
        self._limit_bytes = settings.stt_max_upload_mb * 1024 * 1024
        self._ffmpeg = shutil.which("ffmpeg")

    @property
    def provider_name(self) -> str:
        return f"whisper_api:{self._model}"

    async def aclose(self) -> None:
        await self._client.close()

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        diarize: bool = True,
        num_speakers: int | None = None,
    ) -> TranscriptionResult:
        source = Path(audio_path)
        if not source.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        with tempfile.TemporaryDirectory(prefix="talkwise_stt_") as tmp:
            parts = await asyncio.to_thread(self._prepare_parts, source, Path(tmp))
            segments: list[TranscriptSegment] = []
            detected = "en"
            offset = 0.0
            for part in parts:
                result = await self._transcribe_file(part, language)
                detected = LANGUAGE_CODES.get(str(_field(result, "language", "")).lower(), detected)
                part_segments = _field(result, "segments", None) or []
                for seg in part_segments:
                    text = str(_field(seg, "text", "")).strip()
                    if not text:
                        continue
                    logprob = _field(seg, "avg_logprob", None)
                    segments.append(TranscriptSegment(
                        speaker="SPEAKER_00",
                        start=round(offset + float(_field(seg, "start", 0.0)), 2),
                        end=round(offset + float(_field(seg, "end", 0.0)), 2),
                        text=text,
                        confidence=round(math.exp(logprob), 3) if logprob is not None else None,
                    ))
                offset += float(_field(result, "duration", 0.0) or PART_SECONDS)

        _assign_speakers_by_pauses(segments)
        duration = segments[-1].end if segments else 0.0
        logger.info("Hosted transcription complete", model=self._model, segments=len(segments), duration=duration)
        return TranscriptionResult(
            language=detected,
            duration=duration,
            segments=segments,
            full_text=" ".join(s.text for s in segments),
        )

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=4, max=30))
    async def _transcribe_file(self, path: Path, language: str | None):
        kwargs: dict = {
            "model": self._model,
            "response_format": "verbose_json",
            "timestamp_granularities": ["segment"],
        }
        if language:
            kwargs["language"] = language
        with path.open("rb") as f:
            return await self._client.audio.transcriptions.create(file=f, **kwargs)

    def _prepare_parts(self, source: Path, tmp: Path) -> list[Path]:
        """Compress to 16 kHz mono MP3 and split if it's still over the upload limit."""
        if not self._ffmpeg:
            if source.suffix.lower() in UPLOADABLE and source.stat().st_size <= self._limit_bytes:
                return [source]
            raise RuntimeError(
                "ffmpeg is required to convert this recording for transcription. Install it (brew install ffmpeg)."
            )

        compressed = tmp / "audio.mp3"
        self._ffmpeg_run(["-i", str(source), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k", str(compressed)])
        if compressed.stat().st_size <= self._limit_bytes:
            return [compressed]

        self._ffmpeg_run([
            "-i", str(compressed), "-f", "segment", "-segment_time", str(PART_SECONDS),
            "-c", "copy", str(tmp / "part_%03d.mp3"),
        ])
        return sorted(tmp.glob("part_*.mp3"))

    def _ffmpeg_run(self, args: list[str]) -> None:
        proc = subprocess.run(
            [self._ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *args],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Couldn't read the recording with ffmpeg: {proc.stderr.strip()[:300]}")


def _assign_speakers_by_pauses(segments: list[TranscriptSegment]) -> None:
    """Rough two-speaker guess: a long pause usually means the other person is speaking."""
    speaker = 0
    for i, seg in enumerate(segments):
        if i and seg.start - segments[i - 1].end > SPEAKER_CHANGE_GAP:
            speaker = 1 - speaker
        seg.speaker = f"SPEAKER_{speaker:02d}"
