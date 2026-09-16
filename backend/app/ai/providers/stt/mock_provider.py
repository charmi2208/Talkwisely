"""
Mock STT Provider — generates realistic transcripts without running Whisper.

Used when STT_PROVIDER=mock. Returns a plausible multi-speaker transcript
for any audio file, making the platform demonstrable without GPU/CPU processing.
"""

import asyncio
import random

from app.ai.providers.base import (
    SpeechToTextProvider,
    TranscriptSegment,
    TranscriptionResult,
    TranscriptWord,
)
from app.core.logging import get_logger

logger = get_logger("mock_stt")

# Sample enterprise sales call transcript for demo
_MOCK_SEGMENTS = [
    (0.0, 5.5, "SPEAKER_00", "Good morning! This is James from TalkWiseAI. Am I speaking with Sarah?"),
    (5.8, 10.2, "SPEAKER_01", "Yes, hi James! Sarah Chen here, IT Director at Meridian Financial."),
    (10.5, 18.3, "SPEAKER_00", "Great to connect, Sarah. Thanks for taking the time. I understand you're evaluating communication platforms for your organization?"),
    (18.6, 35.0, "SPEAKER_01", "That's right. We're currently on an old Avaya PBX system and honestly it's costing us a fortune — about eight thousand dollars a month — and we get absolutely zero analytics from it."),
    (35.4, 52.0, "SPEAKER_00", "That's a very common situation we see, especially with financial services firms. When you say zero analytics, what specifically are you missing?"),
    (52.3, 78.5, "SPEAKER_01", "Well, our managers have no idea what's happening on customer calls. We can't monitor call quality, we have no idea how our agents are performing, and our reps have to manually update Salesforce after every single call which is a huge time sink."),
    (79.0, 105.0, "SPEAKER_00", "Understood. So you need AI-powered call analytics, agent performance monitoring, and automated CRM updates. Those are all core to what we do. Let me give you a quick overview of TalkWiseAI."),
    (105.5, 112.0, "SPEAKER_01", "Sure, go ahead."),
    (112.3, 165.0, "SPEAKER_00", "So TalkWiseAI is a conversation intelligence platform built on top of a cloud PBX. Every call is automatically transcribed, analyzed by AI, and the insights — sentiment, intent, action items, objections — are extracted automatically. And yes, we have a native Salesforce integration."),
    (165.5, 185.0, "SPEAKER_01", "That sounds interesting. How does the Salesforce sync actually work? Is it one-way or two-way?"),
    (185.5, 210.0, "SPEAKER_00", "It's bi-directional. After each call, the AI generates a call summary, updates the contact record, logs the activity, and can even move the opportunity stage based on what was discussed. Your reps never have to manually update Salesforce again."),
    (210.5, 230.0, "SPEAKER_01", "Okay, that's actually impressive. We have about 200 people who would need this across our three offices. What does pricing look like for something that size?"),
    (230.5, 260.0, "SPEAKER_00", "For a 200-seat enterprise deployment, we're looking at our enterprise tier. I'll send you a detailed pricing proposal today, but broadly speaking you'd be looking at something comparable to or better than your current spend with significantly more capability."),
    (260.5, 280.0, "SPEAKER_01", "We handle financial data, so I do need to ask about data security and compliance. Are you SOC 2 compliant?"),
    (280.5, 305.0, "SPEAKER_00", "Yes, we are SOC 2 Type II certified. I'll send you our compliance documentation along with the pricing. We also have data residency options if that's important for your regulatory requirements."),
    (305.5, 325.0, "SPEAKER_01", "Good. We've also been looking at RingCentral and we briefly trialed 8x8 last year, but they didn't really have the AI analytics depth we needed."),
    (325.5, 355.0, "SPEAKER_00", "That's actually where we differentiate significantly. Our AI pipeline goes much deeper than basic call transcription — we do sentiment analysis, objection detection, buying signal identification, and we generate coaching recommendations for each agent after every call."),
    (355.5, 375.0, "SPEAKER_01", "The coaching part is interesting. How long does implementation take? We really can't have any downtime."),
    (375.5, 400.0, "SPEAKER_00", "Great question. We use a phased migration approach. We run parallel systems during cutover, so there's zero downtime. Typical enterprise deployment is four to six weeks from contract signing."),
    (400.5, 415.0, "SPEAKER_01", "Four to six weeks is workable. We're looking at doing this in Q3."),
    (415.5, 435.0, "SPEAKER_00", "Perfect, that's very achievable. Sarah, would it make sense to schedule a technical demo this week? I can show you the full platform with a live Salesforce integration demo."),
    (435.5, 455.0, "SPEAKER_01", "Yes, I'd love to see it in action with our Salesforce setup. I'll block Thursday at two o'clock in my calendar. Does that work?"),
    (455.5, 475.0, "SPEAKER_00", "Thursday at two works perfectly. I'll send a calendar invite right away. I'll also send the enterprise pricing proposal and the SOC 2 documentation before then."),
    (475.5, 490.0, "SPEAKER_01", "Great. And can you also connect me with your technical architect? I have some specific API integration questions."),
    (490.5, 510.0, "SPEAKER_00", "Absolutely. I'll loop in our solutions architect on the demo call. He can answer all the technical questions in detail."),
    (510.5, 525.0, "SPEAKER_01", "Perfect. This has been very helpful, James. Looking forward to Thursday."),
    (525.5, 535.0, "SPEAKER_00", "Likewise, Sarah! Talk soon. Have a great morning."),
    (535.5, 540.0, "SPEAKER_01", "You too. Bye!"),
]


class MockSTTProvider(SpeechToTextProvider):
    """Returns a pre-built realistic transcript for demo purposes."""

    def __init__(self) -> None:
        logger.info("Using MOCK STT provider — set STT_PROVIDER=whisper_local for real transcription")

    @property
    def provider_name(self) -> str:
        return "mock"

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        diarize: bool = True,
        num_speakers: int | None = None,
    ) -> TranscriptionResult:
        # Simulate processing time
        await asyncio.sleep(2.0)

        segments: list[TranscriptSegment] = []
        for start, end, speaker, text in _MOCK_SEGMENTS:
            segments.append(
                TranscriptSegment(
                    speaker=speaker,
                    start=start,
                    end=end,
                    text=text,
                    confidence=round(random.uniform(0.92, 0.99), 3),
                )
            )

        full_text = " ".join(s.text for s in segments)
        duration = _MOCK_SEGMENTS[-1][1]

        logger.info("Mock transcription complete", segments=len(segments), duration=duration)

        return TranscriptionResult(
            language=language or "en",
            duration=duration,
            segments=segments,
            full_text=full_text,
        )
