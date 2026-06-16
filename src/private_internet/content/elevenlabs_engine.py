"""ElevenLabs text-to-speech for SIGNAL narration.

Drop-in replacement for PollyEngine: same synthesize_section(text, voice_id,
language_code, output_path) -> duration_ms contract, so video_job can swap
engines by config. Uses eleven_multilingual_v2 so one voice can narrate any
language (the voice is chosen per language via content/voice_config.py).
Synchronous (urllib) — video_job calls it via run_in_executor like Polly.
"""

import json
import logging
import urllib.request

from private_internet.config import get_settings
from private_internet.content.polly_engine import PollyEngine
from private_internet.content.voice_config import get_voice_id

logger = logging.getLogger(__name__)

_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"

# Amazon Polly narration voice used on the fallback path (en-US, neutral). Polly
# runs off the EC2 IAM role — no external key — so it is the reliable safety net
# when ElevenLabs is unavailable (bad key → 401, exhausted quota → 429).
_POLLY_FALLBACK_VOICE = "Joanna"


class ElevenLabsEngine:
    """Synthesizes narration audio per script section via ElevenLabs."""

    def __init__(self):
        s = get_settings()
        self._key = s.elevenlabs_api_key
        self._model = s.elevenlabs_model_id
        if not self._key:
            raise RuntimeError("ELEVENLABS_API_KEY not configured")

    def synthesize_section(
        self,
        text: str,
        voice_id: str,
        language_code: str,   # unused: the multilingual model infers from text
        output_path: str,
    ) -> int:
        """Synthesize `text` to an mp3 at `output_path`. Returns duration in ms."""
        body = json.dumps({
            "text": text,
            "model_id": self._model,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }).encode()
        req = urllib.request.Request(
            _TTS_URL.format(voice_id=voice_id),
            data=body,
            headers={
                "xi-api-key": self._key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            audio = resp.read()
        with open(output_path, "wb") as f:
            f.write(audio)
        # Reuse Polly's ffprobe-based duration probe (same mp3 output).
        return PollyEngine._probe_duration_ms(output_path)


def get_tts_engine():
    """Return the configured narration engine, falling back to Polly when
    ElevenLabs isn't selected or isn't configured (so deploys never break)."""
    s = get_settings()
    if (s.tts_engine or "polly").lower() == "elevenlabs" and s.elevenlabs_api_key:
        return ElevenLabsEngine()
    return PollyEngine()


def synthesize_narration(text: str, language_code: str, output_path: str) -> int:
    """Synthesize narration to an mp3 at ``output_path``; returns duration in ms.

    Engine chain: ElevenLabs (when ``tts_engine=elevenlabs`` and a key is set) →
    Amazon Polly on ANY ElevenLabs failure (invalid key → 401, quota → 429,
    network, etc.). This guarantees narration always completes, so a dead
    ElevenLabs key can never hard-fail SIGNAL/STORIES video assembly — it just
    degrades the voice to Polly until a valid key is restored. Each engine gets
    the voice id it expects (ElevenLabs per-language voice vs a real Polly voice).
    """
    s = get_settings()
    if (s.tts_engine or "polly").lower() == "elevenlabs" and s.elevenlabs_api_key:
        try:
            return ElevenLabsEngine().synthesize_section(
                text, get_voice_id(language_code), language_code, output_path
            )
        except Exception as exc:
            logger.warning(
                "ElevenLabs narration failed (%s) — falling back to Amazon Polly", exc
            )
    return PollyEngine().synthesize_section(
        text, _POLLY_FALLBACK_VOICE, language_code, output_path
    )
