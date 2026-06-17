"""fal.ai image-slide fallback tier for SIGNAL / PULSE / STORIES video clips.

When a video model (Wan2.1 or Kling) fails to produce a clip, this module
generates a still image via the existing fal.ai FLUX backend and renders it as
a Ken Burns (slow zoom) mp4 of the requested duration. The result has genuine
motion — much better than a flat solid-colour card — while costing only a
FLUX schnell call (~$0.003).

Fallback hierarchy (Section 4 / video_assembler wires the call order):

    SIGNAL / PULSE: WAN → image-slide (Ken Burns) → colour card
    STORIES:        Kling → WAN → image-slide (Ken Burns) → colour card

This module is responsible ONLY for the image-slide tier. Colour-card is the
last-resort implemented in video_assembler.py::generate_fallback_card.

FFmpeg recipe
-------------
Mirrors _build_kenburns_clip in ffmpeg_assembler.py (do NOT edit that file —
the recipe here is reproduced to keep this module self-contained and avoid an
import from a module owned by Section 4).

    scale={W}:{H},
    zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))':d={frames}:s={W}x{H}:fps={FPS}
    format=yuv420p

Starting zoom 1.5 × → slowly decreasing toward 1.0, giving a gentle pull-back
motion. d is the total number of output frames (duration × fps).
"""

import asyncio
import logging
import os
import subprocess
import tempfile
from typing import Optional

from private_internet.content.fal_image import generate_image

logger = logging.getLogger(__name__)

# Output encoding parameters — match ffmpeg_assembler.py constants so a slide
# clip concatenates cleanly with any WAN/Kling clip in the same assembly.
_FPS = 24
_WIDTH = 1280
_HEIGHT = 720


class SlideClipError(Exception):
    """Raised when generate_slide_clip cannot produce the mp4.

    Callers should catch this and fall to the flat colour card.
    """


def _run_ffmpeg(args: list[str]) -> None:
    """Run an FFmpeg command; raise SlideClipError on non-zero exit."""
    try:
        subprocess.run(args, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        logger.error("FFmpeg failed in slide_clip: %s\n%s", " ".join(args), stderr)
        raise SlideClipError(f"FFmpeg command failed: {stderr[-2000:]}") from e
    except FileNotFoundError as e:
        raise SlideClipError("ffmpeg not found — install with: sudo apt install ffmpeg") from e


async def generate_slide_clip(
    prompt: str,
    duration_s: int,
    out_path: str,
    *,
    aspect_ratio: str = "16:9",
    image_width: Optional[int] = None,
    image_height: Optional[int] = None,
) -> None:
    """Generate a Ken Burns mp4 from a fal.ai FLUX image.

    Generates one image from `prompt` using fal_image.generate_image, then
    renders a Ken Burns (slow zoom-out) mp4 of `duration_s` seconds at
    1280×720 (or portrait if aspect_ratio is "9:16") into `out_path`.

    Args:
        prompt:       Visual description — same prompt that would go to a video
                      model; FLUX handles scene descriptions well.
        duration_s:   Clip duration in seconds.
        out_path:     Absolute path where the mp4 should be written.
        aspect_ratio: "16:9" (default, 1280×720) or "9:16" (720×1280).
        image_width:  Override fal image generation width; defaults to clip width.
        image_height: Override fal image generation height; defaults to clip height.

    Raises:
        SlideClipError: If fal image generation fails OR ffmpeg fails. Callers
                        should fall to a flat colour card on this exception.
    """
    # Resolve output dimensions from aspect ratio.
    if aspect_ratio == "9:16":
        out_w, out_h = _HEIGHT, _WIDTH   # 720 wide × 1280 tall
    else:
        out_w, out_h = _WIDTH, _HEIGHT   # 1280 wide × 720 tall

    gen_w = image_width or out_w
    gen_h = image_height or out_h

    # Step 1 — generate the image via fal.ai FLUX.
    logger.info("slide_clip: generating image for prompt (first 80 chars): %.80s", prompt)
    try:
        img_bytes = await generate_image(prompt, width=gen_w, height=gen_h)
    except Exception as exc:
        # Wrap any fal.ai error (missing key, bad response, etc.) so callers
        # only need to catch SlideClipError.
        raise SlideClipError(f"fal image generation failed: {exc}") from exc

    if not img_bytes:
        raise SlideClipError("fal image generation returned empty bytes")

    # Step 2 — write image to a temp file and render Ken Burns via FFmpeg.
    # Use the caller's out_path directory so there is no cross-device rename.
    out_dir = os.path.dirname(os.path.abspath(out_path)) or tempfile.gettempdir()
    img_fd, img_path = tempfile.mkstemp(dir=out_dir, suffix=".png")
    try:
        with os.fdopen(img_fd, "wb") as f:
            f.write(img_bytes)

        duration_frames = max(1, duration_s * _FPS)

        # Ken Burns filter — slow zoom-out from 1.5× to ~1.0×. The zoompan
        # filter requires the source to be scaled to the output size first;
        # format=yuv420p ensures libx264 compatibility. This recipe is
        # intentionally identical to VideoAssembler._build_kenburns_clip so
        # slide clips concatenate with video clips without re-encoding.
        zoompan = (
            f"scale={out_w}:{out_h},"
            f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))'"
            f":d={duration_frames}:s={out_w}x{out_h}:fps={_FPS},"
            f"format=yuv420p"
        )

        logger.info(
            "slide_clip: rendering Ken Burns clip: %ss, %dx%d, frames=%d → %s",
            duration_s, out_w, out_h, duration_frames, out_path,
        )

        # -loop 1 holds the still image for as long as needed. -t caps the
        # output duration; the zoompan filter also limits it via d= but -t is
        # a safety net in case duration_frames drifts.
        _run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", img_path,
            "-vf", zoompan,
            "-c:v", "libx264",
            "-r", str(_FPS),
            "-t", str(duration_s),
            "-pix_fmt", "yuv420p",
            out_path,
        ])

    finally:
        # Always clean up the temp image — the caller owns out_path.
        try:
            os.unlink(img_path)
        except OSError:
            pass

    logger.info("slide_clip: done → %s", out_path)
