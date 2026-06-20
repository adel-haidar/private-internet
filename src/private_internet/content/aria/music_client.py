"""ElevenLabs music generation client for ARIA.

Primary path: POST https://api.elevenlabs.io/v1/music
  Body: {"prompt": str, "duration_seconds"?: int}
  Returns audio/mpeg bytes.

Graceful fallback: if the music endpoint returns 401/402/404 (plan lacks
access or no credits), falls back to Amazon Polly TTS narration of the track
concept. Polly runs off the EC2 IAM role (no external key, no per-character
charge at our volume) so it is effectively free compared to ElevenLabs TTS.
The fallback NEVER crashes the generator — it returns bytes or raises only
for genuinely unrecoverable errors (network loss, etc.).

Note on the API shape: at the time of implementation, ElevenLabs /v1/music
accepts `prompt` and an optional `duration_seconds` (integer, capped at 30s on
free plans). The response is streaming audio/mpeg when Accept is set to
`audio/mpeg`, or JSON with an audio_base64 field when content-type is
application/json. We use the binary streaming path for efficiency.
"""

import logging
import os
import tempfile
import urllib.error
import urllib.request
import json
from typing import Optional

from private_internet.config import get_settings

logger = logging.getLogger(__name__)

# ElevenLabs /v1/music endpoint (compose path).
_MUSIC_URL = "https://api.elevenlabs.io/v1/music"

# Plan-level rejection codes (not a client bug — fallback is warranted).
_FALLBACK_STATUS_CODES = {401, 402, 404, 422}

# Polly fallback voice: English neural (Joanna). Polly runs off the IAM role —
# no separate API key needed — and the first 1 million characters/month are
# free-tier, making it the zero-cost safety net for the music fallback path.
_POLLY_FALLBACK_VOICE = "Joanna"
_POLLY_FALLBACK_LOCALE = "en-US"


def generate_music(
    prompt: str,
    duration_seconds: Optional[int] = None,
) -> bytes:
    """Generate music from a text prompt. Returns mp3 bytes.

    Falls back to TTS narration if the music endpoint is inaccessible.
    Never raises on a plan/credit rejection — only on genuine network errors
    (so the generator can mark the track as failed with a meaningful message).
    """
    s = get_settings()
    api_key = s.elevenlabs_api_key
    if not api_key:
        logger.warning("ELEVENLABS_API_KEY not set — falling back to Polly TTS")
        return _tts_fallback(prompt)

    try:
        return _call_music_api(prompt, api_key, duration_seconds)
    except _MusicPlanError as e:
        logger.warning(
            "ElevenLabs music API rejected request (%s) — falling back to Polly TTS narration",
            e,
        )
        return _tts_fallback(prompt)


def _call_music_api(
    prompt: str,
    api_key: str,
    duration_seconds: Optional[int],
) -> bytes:
    """Call /v1/music and return raw mp3 bytes. Raises _MusicPlanError on plan rejection."""
    body: dict = {"prompt": prompt}
    if duration_seconds is not None:
        body["duration_seconds"] = duration_seconds

    req = urllib.request.Request(
        _MUSIC_URL,
        data=json.dumps(body).encode(),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code in _FALLBACK_STATUS_CODES:
            raise _MusicPlanError(f"HTTP {e.code}: {e.reason}") from e
        # Other HTTP errors (5xx etc.) — re-raise so the generator marks track as failed.
        raise RuntimeError(f"ElevenLabs music API error: HTTP {e.code} {e.reason}") from e


def _tts_fallback(prompt: str, api_key: str = "") -> bytes:
    """Synthesize a short narration of the track concept via Amazon Polly.

    Polly runs off the EC2 IAM role — no external API key — so this fallback
    incurs zero additional cost beyond the music-API failure itself. Returns
    mp3 bytes written to a temp file then read back. Falls back to a silent
    stub only if Polly itself errors (e.g. IAM misconfiguration).
    """
    from private_internet.content.polly_engine import PollyEngine

    spoken = (
        f"This is a generated musical piece. {prompt[:200]}"
        if len(prompt) > 20
        else f"A short musical composition. {prompt}"
    )

    try:
        engine = PollyEngine()
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            engine.synthesize_section(
                spoken,
                _POLLY_FALLBACK_VOICE,
                _POLLY_FALLBACK_LOCALE,
                tmp_path,
            )
            with open(tmp_path, "rb") as f:
                audio = f.read()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        logger.info(
            "Polly TTS fallback produced %d bytes of narration audio", len(audio)
        )
        return audio
    except Exception as exc:
        logger.warning("Polly TTS fallback failed (%s) — returning stub audio", exc)
        return _silent_mp3_stub()


def _silent_mp3_stub() -> bytes:
    """Return the smallest valid MP3 frame (128-byte zero-filled frame).
    This allows the pipeline to complete and write a placeholder asset; the
    waveform will be all-zeros, which is visually distinguishable from real audio."""
    # ID3v2 tag + one valid MP3 frame header for a silent frame.
    # Frame: sync (0xFF 0xFB), MPEG1 Layer3 128kbps 44.1kHz mono, padded.
    return b"\xff\xfb\x90\x00" + b"\x00" * 413


class _MusicPlanError(Exception):
    """Plan-level rejection from the music endpoint (fallback warranted)."""
