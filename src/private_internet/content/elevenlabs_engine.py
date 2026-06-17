"""ElevenLabs text-to-speech for SIGNAL narration.

Drop-in replacement for PollyEngine: same synthesize_section(text, voice_id,
language_code, output_path) -> duration_ms contract, so video_job can swap
engines by config. Uses eleven_multilingual_v2 so one voice can narrate any
language (the voice is chosen per language via content/voice_config.py).
Synchronous (urllib) — video_job calls it via run_in_executor like Polly.
"""

import json
import logging
import os
import subprocess
import urllib.request

from private_internet.config import get_settings
from private_internet.content.polly_engine import PollyEngine
from private_internet.content.voice_config import get_voice_id

logger = logging.getLogger(__name__)

_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128"

# Amazon Polly fallback voices per language: (voice_id, Polly locale). Polly runs
# off the EC2 IAM role — no external key — so it is the reliable safety net when
# ElevenLabs is unavailable (bad key → 401, exhausted quota → 429). Polly requires
# a full locale ("en-US", not "en") and a real voice id; the Arabic/Russian voices
# are standard-only and PollyEngine retries the standard engine automatically.
_POLLY_VOICES: dict[str, tuple[str, str]] = {
    "en": ("Joanna", "en-US"),
    "de": ("Vicki", "de-DE"),
    "fr": ("Lea", "fr-FR"),
    "ru": ("Tatyana", "ru-RU"),
    "ar": ("Zeina", "arb"),
}
_POLLY_DEFAULT = ("Joanna", "en-US")

# Duration of generated silence for scenes with no narration text (ms).
_SILENCE_DURATION_MS = 500


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


def _synthesize_one(text: str, language_code: str, output_path: str) -> int:
    """Synthesize a single narration text to ``output_path``; returns duration ms.

    Applies the same ElevenLabs → Polly fallback chain used by
    ``synthesize_narration``.  Extracted so both ``synthesize_narration`` and
    ``synthesize_scene_narrations`` share identical engine-selection logic
    without duplication.
    """
    s = get_settings()
    if (s.tts_engine or "polly").lower() == "elevenlabs" and s.elevenlabs_api_key:
        try:
            return ElevenLabsEngine().synthesize_section(
                text, get_voice_id(language_code), language_code, output_path
            )
        except Exception as exc:
            logger.warning(
                "ElevenLabs synthesis failed (%s) — falling back to Amazon Polly", exc
            )
    # Polly needs a real voice + full locale; map on the primary language subtag
    # ("en-US" → "en") and default to English for anything unmapped.
    voice_id, locale = _POLLY_VOICES.get(
        language_code.split("-")[0].lower(), _POLLY_DEFAULT
    )
    return PollyEngine().synthesize_section(text, voice_id, locale, output_path)


def _synthesize_silence(output_path: str, duration_ms: int = _SILENCE_DURATION_MS) -> int:
    """Write a short silent mp3 to ``output_path`` using ffmpeg anullsrc.

    No network call, no TTS provider, no additional dependencies — ffmpeg is
    already required by the video pipeline.  Returns the measured duration in ms
    (probed from the written file so the caller gets an accurate value even if
    the requested duration is not exactly representable in mp3 frame boundaries).
    """
    duration_s = duration_ms / 1000.0
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono",
            "-t", str(duration_s),
            "-q:a", "9",
            "-acodec", "libmp3lame",
            output_path,
        ],
        check=True,
        capture_output=True,
    )
    return PollyEngine._probe_duration_ms(output_path)


def synthesize_narration(text: str, language_code: str, output_path: str) -> int:
    """Synthesize narration to an mp3 at ``output_path``; returns duration in ms.

    Engine chain: ElevenLabs (when ``tts_engine=elevenlabs`` and a key is set) →
    Amazon Polly on ANY ElevenLabs failure (invalid key → 401, quota → 429,
    network, etc.). This guarantees narration always completes, so a dead
    ElevenLabs key can never hard-fail SIGNAL/STORIES video assembly — it just
    degrades the voice to Polly until a valid key is restored. Each engine gets
    the voice id it expects (ElevenLabs per-language voice vs a real Polly voice).
    """
    return _synthesize_one(text, language_code, output_path)


def synthesize_scene_narrations(
    scenes: list[dict],
    language_code: str,
    work_dir: str,
) -> list[dict]:
    """Synthesize one mp3 per scene; returns a list aligned to ``scenes``.

    Each entry in the returned list corresponds to the same-index entry in
    ``scenes`` and has the shape::

        {"scene_number": int, "audio_path": str, "duration_ms": int}

    Engine chain per scene: ElevenLabs → Polly fallback (same as
    ``synthesize_narration``).  A failure on one scene degrades that scene to
    Polly without aborting the rest of the batch.

    Scenes whose ``narration_text`` is absent or whitespace-only receive a
    brief silent track (``_SILENCE_DURATION_MS`` ms, ~500 ms) so every scene
    always has a valid ``audio_path`` and ``duration_ms`` that Section 4's
    assembler can align against its video clip.

    Audio files are written to ``work_dir/scene_audio_{scene_number:04d}.mp3``.
    The function is synchronous; callers that need async should wrap it with
    ``asyncio.get_event_loop().run_in_executor``.
    """
    os.makedirs(work_dir, exist_ok=True)
    results: list[dict] = []

    for scene in scenes:
        scene_number = int(scene["scene_number"])
        narration_text = (scene.get("narration_text") or "").strip()
        output_path = os.path.join(work_dir, f"scene_audio_{scene_number:04d}.mp3")

        if not narration_text:
            # Empty narration: generate silence rather than calling any TTS provider.
            logger.debug(
                "Scene %d has no narration text — generating %d ms of silence",
                scene_number, _SILENCE_DURATION_MS,
            )
            try:
                duration_ms = _synthesize_silence(output_path)
            except Exception as exc:
                # ffmpeg failure is very unlikely but must not crash the batch.
                logger.error(
                    "Failed to generate silence for scene %d (%s) — using nominal duration",
                    scene_number, exc,
                )
                duration_ms = _SILENCE_DURATION_MS
        else:
            try:
                duration_ms = _synthesize_one(narration_text, language_code, output_path)
                logger.debug(
                    "Scene %d audio: %d ms → %s", scene_number, duration_ms, output_path
                )
            except Exception as exc:
                # Last-resort guard: if both ElevenLabs and Polly fail, fall back
                # to silence so the assembler can still produce a (muted) video
                # rather than crashing the whole job.
                logger.error(
                    "All TTS engines failed for scene %d (%s) — substituting silence",
                    scene_number, exc,
                )
                try:
                    duration_ms = _synthesize_silence(output_path)
                except Exception as silence_exc:
                    logger.error(
                        "Silence generation also failed for scene %d (%s)",
                        scene_number, silence_exc,
                    )
                    duration_ms = _SILENCE_DURATION_MS

        results.append({
            "scene_number": scene_number,
            "audio_path": output_path,
            "duration_ms": duration_ms,
        })

    return results
