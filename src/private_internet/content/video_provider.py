"""Video generation provider routing — the single source of truth.

Video clips are split across providers by content type and fallback tier:

  - Wan2.1 (Replicate)    → SIGNAL + PULSE  — high volume, cost-efficient 720p
  - Kling (fal.ai)        → STORIES         — cinematic, long-form
  - Image-slide (fal.ai)  → all types       — fallback before colour card;
                                               FLUX image + Ken Burns FFmpeg mp4
  - Colour card (FFmpeg)  → all types       — last resort, no motion

The fallback hierarchy per content type:

    SIGNAL / PULSE:
      1. WAN (Replicate)         → primary
      2. Image-slide (Ken Burns) → fal FLUX image + FFmpeg
      3. Colour card             → last resort

    STORIES:
      1. Kling (fal.ai)          → primary
      2. WAN (Replicate)         → first fallback
      3. Image-slide (Ken Burns) → fal FLUX image + FFmpeg
      4. Colour card             → last resort

The mapping below is the ONLY place that decides which provider a content type
uses. No other module contains routing logic. If the rule changes, it changes
here and nowhere else.

Section 4 (video_assembler.py) wires the actual call order using these
providers plus the slide_clip.generate_slide_clip function for the image-slide
tier and generate_fallback_card for the colour card.
"""

import logging

logger = logging.getLogger(__name__)


VIDEO_PROVIDER_MAP: dict[str, str] = {
    "stories": "kling",   # heavy lifting — cinematic, long-form
    "signal":  "wan2",    # high volume — cost-efficient 720p
    "pulse":   "wan2",    # visual content — cost-efficient 720p
}


def get_provider(content_type: str) -> str:
    """
    Returns the primary video generation provider for a given content type.
    Deterministic. No LLM. No dynamic logic.
    content_type: 'stories' | 'signal' | 'pulse'
    """
    provider = VIDEO_PROVIDER_MAP.get(content_type)
    if provider is None:
        raise ValueError(
            f"Unknown content_type '{content_type}'. "
            f"Must be one of: {list(VIDEO_PROVIDER_MAP.keys())}"
        )
    return provider


# Estimated per-clip cost in EUR. Not used for billing — only for the internal
# cost log so monthly generation spend can be queried per provider/content type.
#
# wan2:        wavespeedai/wan-2.1-t2v-720p at $0.07/s; ~8s clip ≈ $0.56 ≈ 0.52 EUR.
#              (Old wan-video/wan-2.1-1.3b was $0.20/clip fixed — 480p, 5s only.)
# kling:       fal.ai Kling v1 Standard at ~$1.50/clip (5–10s). Adjust per model.
# slide:       fal.ai FLUX schnell image (~$0.003) + FFmpeg (near-zero). Effectively
#              the cheapest fallback that still provides motion.
# colour_card: FFmpeg only — zero API cost.
#
# Update as Replicate / fal.ai pricing changes.
ESTIMATED_COST_EUR = {
    "wan2":        0.52,   # per clip — Wan2.1 720p on Replicate (~8s @ $0.07/s)
    "kling":       1.40,   # per clip — Kling (fal.ai) Standard tier
    "slide":       0.003,  # per clip — FLUX schnell image + FFmpeg Ken Burns
    "colour_card": 0.00,   # per clip — FFmpeg only
}


def log_generation_cost(
    provider: str,
    content_type: str,
    scene_number: int,
    is_fallback: bool,
) -> None:
    """
    Logs estimated cost per clip for monitoring.
    Not used for billing — only for internal cost tracking.

    `provider` may be "wan2", "kling", "slide", or "colour_card".
    """
    cost = ESTIMATED_COST_EUR.get(provider, 0.0)
    logger.info(
        "video_clip_generated",
        extra={
            "provider": provider,
            "content_type": content_type,
            "scene_number": scene_number,
            "is_fallback": is_fallback,
            "estimated_cost_eur": cost,
        },
    )
