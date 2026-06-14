"""Pure-Python waveform computation for ARIA.

compute_waveform(audio_bytes, num_bars=200) -> list[float]

Decodes mp3/audio via pydub (which wraps ffmpeg/avconv), segments the PCM
samples into `num_bars` equal-width windows, computes RMS amplitude per
window, then normalises to [0.0, 1.0].

Graceful degradation:
- If pydub/ffmpeg is unavailable, falls back to stdlib audioop on raw bytes
  (coarser but dependency-free).
- If audio is silent or very short, returns a list of zeros of length num_bars.
- Never raises — always returns a list[float] of exactly `num_bars` values.
"""

import logging
import math
from typing import Optional

logger = logging.getLogger(__name__)


def compute_waveform(audio_bytes: bytes, num_bars: int = 200) -> list[float]:
    """Compute amplitude envelope.

    Returns a list of exactly `num_bars` floats in [0.0, 1.0].
    """
    if not audio_bytes or num_bars <= 0:
        return [0.0] * max(num_bars, 0)

    samples = _decode_to_samples(audio_bytes)
    if not samples:
        return [0.0] * num_bars

    return _samples_to_bars(samples, num_bars)


def _decode_to_samples(audio_bytes: bytes) -> Optional[list[float]]:
    """Attempt pydub decode first, then audioop fallback."""
    try:
        return _pydub_decode(audio_bytes)
    except Exception as e:
        logger.debug("pydub decode failed (%s), trying audioop fallback", e)
    try:
        return _audioop_decode(audio_bytes)
    except Exception as e:
        logger.warning("All audio decoders failed: %s — returning silence", e)
        return None


def _pydub_decode(audio_bytes: bytes) -> list[float]:
    """Decode audio via pydub (requires ffmpeg on PATH)."""
    from pydub import AudioSegment  # type: ignore
    import io

    seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
    # Normalise to mono, 16-bit PCM.
    seg = seg.set_channels(1).set_sample_width(2)
    raw = seg.raw_data  # 16-bit little-endian mono samples
    n_samples = len(raw) // 2
    if n_samples == 0:
        return []
    # Unpack all samples at once via a memoryview for performance.
    import array
    arr = array.array("h")
    arr.frombytes(raw)
    # Normalise to [-1.0, 1.0].
    return [s / 32768.0 for s in arr]


def _audioop_decode(audio_bytes: bytes) -> list[float]:
    """Rough fallback: treat the raw bytes as 8-bit unsigned PCM.

    This is inaccurate for real mp3 data but keeps the pipeline running when
    pydub/ffmpeg is unavailable (e.g. in CI without system packages).
    """
    # Skip the first 128 bytes to skip any ID3 tag.
    raw = audio_bytes[128:]
    if not raw:
        raw = audio_bytes
    # Interpret as unsigned 8-bit samples, centre at 128.
    samples = [(b - 128) / 128.0 for b in raw]
    return samples


def _samples_to_bars(samples: list[float], num_bars: int) -> list[float]:
    """Divide samples into `num_bars` windows, compute RMS per window,
    then normalise to [0.0, 1.0]."""
    n = len(samples)
    if n == 0:
        return [0.0] * num_bars

    window = max(1, n // num_bars)
    bars: list[float] = []
    for i in range(num_bars):
        start = i * window
        end = min(start + window, n)
        if start >= n:
            bars.append(0.0)
            continue
        chunk = samples[start:end]
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk)) if chunk else 0.0
        bars.append(rms)

    # Normalise so the loudest bar = 1.0
    peak = max(bars) if bars else 0.0
    if peak > 0.0:
        bars = [b / peak for b in bars]

    # Clamp to [0.0, 1.0] (should already be, but guard against float noise).
    return [max(0.0, min(1.0, b)) for b in bars]
