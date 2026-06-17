"""Replicate client for Wan2.1 video generation.

Used for SIGNAL and PULSE content — high volume, cost-efficient. Wan2.1 is
Alibaba's open-source video-generation model. We use the wavespeedai accelerated
720p variant on Replicate, which supports configurable duration and true 720p
resolution (1280x720). STORIES stays on Kling (see video_provider.py).

Provider decision after investigating fal.ai (2026-06):
  fal.ai does NOT list any WAN model in their public text-to-video catalog.
  The fal-ai/wan namespace exists but requires authentication and is not
  publicly documented — input fields cannot be verified without live credentials.
  We therefore keep Replicate as the WAN provider. Migration to fal.ai would only
  be warranted once fal.ai lists a WAN model with verifiable public docs.

Mirrors the resilience contract of the fal/Kling client (content/fal_video.py):
submit a job, poll until it finishes, then download the resulting mp4 bytes.
Callers keep a colour-card fallback, so an error or timeout degrades gracefully
rather than failing the whole video. A failed SIGNAL/PULSE clip must NEVER fall
through to Kling — that constraint lives in the assembler and protects the cost
model.

The `replicate` SDK is imported lazily (inside the client) so this module — and
the assembler that imports it at module load — never fails to import when the
package or REPLICATE_API_KEY is absent. The error surfaces only when a clip is
actually requested, exactly like the fal client's missing-key behaviour.

Verified model (wavespeedai/wan-2.1-t2v-720p) input fields
------------------------------------------------------------
Source: https://replicate.com/wavespeedai/wan-2.1-t2v-720p (2026-06-17)

  prompt            str    required — text description of the video
  num_frames        int    81–100, default 81  — total output frames
  frames_per_second int    5–24,   default 16  — playback fps
  aspect_ratio      str    "16:9" | "9:16" | "1:1", default "16:9"
                           16:9 → 1280×720 px; 9:16 → 720×1280; 1:1 → 1024×1024
  fast_mode         str    "Off" | "Balanced" | "Fast", default "Balanced"
  sample_steps      int    1–50, default 30
  sample_guide_scale float 1–10, default 5
  sample_shift      float  1–10, default 5

Duration formula: duration_s ≈ num_frames / frames_per_second.
To target T seconds: choose fps such that round(T × fps) falls in [81, 100].
E.g. 5 s → num_frames=100, fps=20  (100/20 = 5.0 s)
     8 s → num_frames=96,  fps=12  (96/12  = 8.0 s)
    10 s → num_frames=100, fps=10  (100/10 = 10.0 s)

Pricing: $0.07 per second of output video (≈ $0.56 for an 8 s clip).
The old 1.3B model billed $0.20 per output video (fixed 5 s 480p).
This model costs more per clip but delivers real 720p + configurable duration.
"""

import asyncio
import logging
import math

import httpx

from private_internet.config import get_settings

logger = logging.getLogger(__name__)

# Default model slug — wavespeedai's accelerated Wan2.1 at 720p with configurable
# duration. Overridable per instance via WAN2_MODEL env var. The old 1.3B fixed
# slug (wan-video/wan-2.1-1.3b) produced only ~5s 480p clips with no duration
# control; this replaces it entirely.
_DEFAULT_WAN2_MODEL = "wavespeedai/wan-2.1-t2v-720p"

# Supported aspect ratio values for the 720p model. 16:9 → 1280×720; other
# values are accepted but kept here for reference validation.
_ASPECT_RATIO_720P = "16:9"

# Duration parameters: supported target seconds and the (num_frames, fps) pair
# that achieves each. All pairs validated against the model's min=81/max=100
# frames constraint and 5–24 fps range. Durations are config-driven via
# wan2_durations in Settings so they can be overridden per instance.
_DURATION_PARAMS: dict[int, tuple[int, int]] = {
    # target_s → (num_frames, frames_per_second)
    5:  (100, 20),   # 100/20 = 5.00 s
    6:  (96,  16),   # 96/16  = 6.00 s
    8:  (96,  12),   # 96/12  = 8.00 s
    10: (100, 10),   # 100/10 = 10.00 s
    16: (81,  5),    # 81/5   = 16.20 s (useful for long sections)
}
_DEFAULT_DURATION_S = 8

POLL_INTERVAL_SECONDS = 5
MAX_POLL_ATTEMPTS = 120   # 10 minutes max


class Wan2GenerationError(Exception):
    pass


def _resolve_duration_params(requested_s: int) -> tuple[int, int]:
    """Return (num_frames, fps) for the closest supported duration.

    Tries exact match first; if none, picks the entry in _DURATION_PARAMS whose
    actual duration (frames/fps) is closest to requested_s. Tie-breaks to the
    longer clip so narration never under-runs the scene.
    """
    if requested_s in _DURATION_PARAMS:
        return _DURATION_PARAMS[requested_s]

    # Snap to nearest available target duration.
    best = min(
        _DURATION_PARAMS.items(),
        key=lambda kv: (abs(kv[0] - requested_s), -kv[0]),
    )
    target_s, params = best
    logger.debug(
        "wan2: requested %ss not in supported set %s; snapped to %ss",
        requested_s, sorted(_DURATION_PARAMS.keys()), target_s,
    )
    return params


class ReplicateWanClient:
    """
    Generates video clips via Wan2.1 (720p) on Replicate.
    Returns raw MP4 bytes per clip.

    Model: wavespeedai/wan-2.1-t2v-720p — 720p, configurable duration,
    accelerated inference. Replaces the old wan-video/wan-2.1-1.3b (fixed
    ~5s 480p, no duration control).

    Duration is achieved by selecting (num_frames, frames_per_second) pairs
    validated against the model's documented field ranges; invalid field names
    or out-of-range values cause Replicate to reject the prediction (HTTP 422),
    so we never guess — all pairs are pre-verified in _DURATION_PARAMS above.
    """

    def __init__(self):
        # Lazy: the replicate.Client is only built on first use, so importing
        # this module never requires the `replicate` package or an API key.
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import replicate  # imported lazily — see module docstring
            except ImportError as e:  # pragma: no cover
                raise Wan2GenerationError(
                    "The 'replicate' package is not installed. "
                    "Run: pip install replicate"
                ) from e
            api_token = get_settings().replicate_api_key
            if not api_token:
                raise Wan2GenerationError("REPLICATE_API_KEY not configured")
            self._client = replicate.Client(api_token=api_token)
        return self._client

    @staticmethod
    def _model() -> str:
        return get_settings().wan2_model or _DEFAULT_WAN2_MODEL

    async def generate_clip(
        self,
        prompt: str,
        duration_seconds: int = _DEFAULT_DURATION_S,
        width: int = 1280,
        height: int = 720,
    ) -> bytes:
        """
        Submits a generation to Replicate, polls until complete,
        returns raw MP4 bytes.

        `duration_seconds` is snapped to the nearest supported value in
        _DURATION_PARAMS. `width`/`height` are accepted for API compatibility
        but the model is configured via aspect_ratio (not pixel dimensions);
        16:9 → 1280×720 is the default.

        Raises Wan2GenerationError on failure or timeout.
        """
        client = self._get_client()

        # Derive (num_frames, fps) for the target duration. Both fields are
        # VERIFIED against the model's documented ranges before forwarding.
        # Never pass a field not listed in the model's schema — Replicate
        # returns HTTP 422 for unknown input keys.
        num_frames, fps = _resolve_duration_params(int(duration_seconds))
        actual_s = num_frames / fps
        logger.debug(
            "wan2: target=%ss → num_frames=%s, fps=%s (actual=%.2fs), model=%s",
            duration_seconds, num_frames, fps, actual_s, self._model(),
        )

        # Determine aspect_ratio from width/height hint if caller deviates from
        # the default; fall back to 16:9 (1280×720) which is always available.
        if width < height:
            aspect_ratio = "9:16"
        else:
            aspect_ratio = "16:9"

        input_params = {
            "prompt": prompt,
            "num_frames": num_frames,
            "frames_per_second": fps,
            "aspect_ratio": aspect_ratio,
            "fast_mode": "Balanced",  # Good quality/speed trade-off
        }

        try:
            prediction = await asyncio.to_thread(
                client.predictions.create,
                model=self._model(),
                input=input_params,
            )
        except Exception as e:
            raise Wan2GenerationError(f"Replicate submission failed: {e}")

        return await self._poll_until_complete(prediction.id)

    async def _poll_until_complete(self, prediction_id: str) -> bytes:
        client = self._get_client()
        for _attempt in range(MAX_POLL_ATTEMPTS):
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

            try:
                prediction = await asyncio.to_thread(
                    client.predictions.get,
                    prediction_id,
                )
            except Exception as e:
                raise Wan2GenerationError(f"Replicate poll failed: {e}")

            if prediction.status == "succeeded":
                output = prediction.output
                # Wan2.1 returns a single video URL; some Replicate models wrap
                # it in a list. Handle both.
                if isinstance(output, list):
                    if not output:
                        raise Wan2GenerationError(
                            f"Wan2.1 prediction {prediction_id} returned no output"
                        )
                    output = output[0]
                if not output:
                    raise Wan2GenerationError(
                        f"Wan2.1 prediction {prediction_id} returned no output"
                    )
                return await self._download_clip(str(output))

            elif prediction.status in ("failed", "canceled"):
                raise Wan2GenerationError(
                    f"Wan2.1 prediction {prediction_id} {prediction.status}: "
                    f"{prediction.error}"
                )
            # status is 'starting' or 'processing' — keep polling

        raise Wan2GenerationError(
            f"Wan2.1 prediction {prediction_id} timed out after "
            f"{MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS}s"
        )

    async def _download_clip(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content


# ---------------------------------------------------------------------------
# Module-level function (for callers that want a simple async function rather
# than the class). Section 4 (video_assembler) uses the class directly via
# ReplicateWanClient, but this is provided for symmetry with generate_video_clip.
# ---------------------------------------------------------------------------
async def generate_wan_clip(
    prompt: str,
    *,
    duration: int = _DEFAULT_DURATION_S,
    aspect_ratio: str = "16:9",
) -> bytes:
    """Generate one Wan2.1 720p clip; return mp4 bytes. Raises Wan2GenerationError."""
    # Map aspect_ratio string to width/height hint for the client.
    width, height = (720, 1280) if aspect_ratio == "9:16" else (1280, 720)
    client = ReplicateWanClient()
    return await client.generate_clip(
        prompt=prompt,
        duration_seconds=duration,
        width=width,
        height=height,
    )
