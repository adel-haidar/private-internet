"""
Shared video assembly pipeline for SIGNAL and STORIES.

No video model (Kling, Veo3, …) generates more than ~2 minutes of coherent
video per call, but STORIES needs 6–45 minutes and SIGNAL needs 3–5. This
module stitches many short clips into one long video:

    translate visuals → generate N clips (per-scene audio budgeted)
                      → per-scene: fit clip to narration duration → mux audio
                      → FFmpeg concat (copy — all clips already uniform)
                      → upload to S3

Per-scene approach (Section 4 rewrite)
---------------------------------------
Each scene's narration is synthesized first so its real duration (ms) is
known before any clip is generated. The video clip for that scene is then
fitted to the narration:
  - If the generated clip is SHORTER than the narration, it is looped.
  - If it is LONGER, it is trimmed to the narration length.
The per-scene clip is then muxed with that scene's audio track. Every clip
leaves assembly in an identical format (1280×720, 24 fps, yuv420p, AAC 192 k)
so the final concat-demuxer step is a lossless copy — no re-encode, no glitch.

Per-clip provider routing + fallback hierarchy
----------------------------------------------
Which provider generates a clip is decided ONLY by content/video_provider.py
(get_provider). The per-provider fallback hierarchy is:

    SIGNAL / PULSE:
      1. Wan2.1 (Replicate)         — primary
      2. Image-slide (Ken Burns)    — fal FLUX image + FFmpeg (new)
      3. Colour card (FFmpeg)       — last resort, no motion
      Never: Kling — too expensive for high-volume content. A failed
             SIGNAL/PULSE clip must NEVER trigger a Kling API call.

    STORIES:
      1. Kling (fal.ai)             — primary
      2. Wan2.1 (Replicate)         — first fallback
      3. Image-slide (Ken Burns)    — fal FLUX image + FFmpeg (new)
      4. Colour card (FFmpeg)       — last resort

"Kling" here is the existing fal.ai client (content/fal_video.generate_video_clip,
configured with a Kling model). It is not modified by the routing.
"""

import asyncio
import inspect
import logging
import math
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Awaitable, Callable, List, Optional, Union

from private_internet.content.asset_store import AssetStore
from private_internet.content.elevenlabs_engine import (
    synthesize_narration,
    synthesize_scene_narrations,
)
from private_internet.content.fal_video import generate_video_clip
from private_internet.content.replicate_wan_client import (
    ReplicateWanClient,
    Wan2GenerationError,
)
from private_internet.content.slide_clip import SlideClipError, generate_slide_clip
from private_internet.content.video_provider import get_provider, log_generation_cost
from private_internet.content.visual_translator import (
    build_final_prompt,
    kling_duration,
    translate_scenes,
)

logger = logging.getLogger(__name__)

MAX_CONCURRENT_KLING_CALLS = 4  # semaphore limit — never exceed (Kling rate limits)

# Normalised output parameters — every per-scene clip must match exactly so the
# concat-demuxer can use stream copy without glitch or re-encode.
_OUT_WIDTH  = 1280
_OUT_HEIGHT = 720
_OUT_FPS    = 24
_OUT_PIX_FMT = "yuv420p"

# Wan2.1 (Replicate) client — module singleton, lazy under the hood (it builds no
# replicate.Client and reads no key until a clip is actually requested), so
# importing this module never needs the package or REPLICATE_API_KEY.
_wan_client = ReplicateWanClient()

# Mood → fallback solid-colour card (used when a clip fails to generate). The
# keys match the visual translator's mood enum. Dark, Calm-Intelligence tints so
# a failed scene degrades quietly.
MOOD_FALLBACK_COLORS = {
    "calm":        "#1A1A28",
    "tense":       "#1A0C0C",
    "warm":        "#1A130C",
    "melancholic": "#0C0C1A",
    "energetic":   "#0C1A0C",
}

# Script scenes carry a scene_type, not a mood — map one to the other for the
# fallback colour when the visual translator did not supply a mood.
_SCENE_TYPE_MOOD = {
    "establishing": "calm",
    "development":  "warm",
    "transition":   "melancholic",
    "climax":       "tense",
    "resolution":   "calm",
}

# Camera/lighting language appended per scene_type when the LLM visual translator
# is unavailable (deterministic + pure-Python so assembly still proceeds without
# sending abstract topic text to Kling).
_SCENE_TYPE_STYLE = {
    "establishing": "wide establishing shot, slow push-in",
    "development":  "medium shot, gentle camera movement",
    "transition":   "sweeping transition, motion blur",
    "climax":       "dramatic close-up, dynamic motion",
    "resolution":   "calm pull-back, settling motion",
}

_FALLBACK_DURATION_DEFAULT = 8
_SEGMENT_SCENE_LIMIT = 50  # STORIES episodes > ~15 min are generated in segments


ProgressCb = Optional[Callable[[dict], Union[None, Awaitable[None]]]]


def _scene_mood(scene: dict) -> str:
    return _SCENE_TYPE_MOOD.get(scene.get("scene_type"), "calm")


def translate_visuals_batch(scenes: List[dict]) -> List[str]:
    """Deterministic fallback translator: turn each scene's visual_description
    into a Kling prompt with cinematic/camera language keyed by scene_type.

    Used only when the LLM visual translator (Prompt 2) returns nothing, so the
    pipeline never sends raw abstract topic text to Kling. Order preserved.
    """
    prompts = []
    for scene in scenes:
        desc = (scene.get("visual_description") or "").strip().rstrip(".")
        style = _SCENE_TYPE_STYLE.get(scene.get("scene_type"), "cinematic shot")
        prompts.append(
            f"{desc}. {style}, cinematic, dark editorial style, "
            "photorealistic, 16:9, no text, no watermark"
        )
    return prompts


def chunk_scenes(scenes: List[dict], size: int = _SEGMENT_SCENE_LIMIT) -> List[List[dict]]:
    """Split scenes into segments (default 50) for memory-bounded assembly of
    long STORIES episodes. Each segment can be assembled then concatenated."""
    return [scenes[i:i + size] for i in range(0, len(scenes), size)] or [[]]


def _check_ffmpeg() -> None:
    """Fail fast with a clear message if FFmpeg is not installed."""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
    except FileNotFoundError:
        result = None
    if result is None or result.returncode != 0:
        raise RuntimeError("FFmpeg not found. Run: sudo apt-get install -y ffmpeg")


def _run_ffmpeg(args: List[str]) -> None:
    result = subprocess.run(args, capture_output=True)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
        logger.error("FFmpeg failed: %s\n%s", " ".join(args), stderr[-2000:])
        raise RuntimeError(f"FFmpeg command failed: {stderr[-1000:]}")


def fallback_card_command(hex_color: str, duration: int, out_path: str) -> List[str]:
    """FFmpeg argv for a solid-colour 1280x720 card of `duration` seconds.
    Matches the normalised output format (_OUT_WIDTH × _OUT_HEIGHT, yuv420p)
    so it concatenates cleanly with real clips."""
    return [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={hex_color}:size={_OUT_WIDTH}x{_OUT_HEIGHT}:duration={duration}",
        "-r", str(_OUT_FPS),
        "-c:v", "libx264", "-pix_fmt", _OUT_PIX_FMT,
        str(out_path),
    ]


def generate_fallback_card(mood: str, duration: int, out_path: str) -> None:
    """Render a mood-coloured fallback card for a scene whose clip failed."""
    hex_color = MOOD_FALLBACK_COLORS.get(mood, MOOD_FALLBACK_COLORS["calm"])
    logger.warning("Using %s fallback card (%s) → %s", mood, hex_color, out_path)
    _run_ffmpeg(fallback_card_command(hex_color, duration, str(out_path)))


def write_concat_manifest(clip_paths: List[str], manifest_path: str) -> str:
    """Write the FFmpeg concat-demuxer manifest (`file '<path>'` per line)."""
    with open(manifest_path, "w") as f:
        for clip_path in clip_paths:
            f.write(f"file '{clip_path}'\n")
    return manifest_path


async def _emit(on_progress: ProgressCb, patch: dict) -> None:
    """Invoke a sync or async progress callback, swallowing its errors so a
    progress-write failure never aborts the assembly."""
    if on_progress is None:
        return
    try:
        result = on_progress(patch)
        if inspect.isawaitable(result):
            await result
    except Exception as exc:  # progress is best-effort
        logger.warning("progress callback failed (ignored): %s", exc)


def _synthesize_narration(narration_text: str, language_code: str, out_path: str) -> None:
    """Generate the full narration mp3 (ElevenLabs → Amazon Polly fallback).

    Kept for callers that still use the monolithic narration path. Within
    assemble_video the per-scene synthesizer is used instead.
    """
    synthesize_narration(narration_text, language_code, out_path)


def _build_clip_plan(script_scenes: List[dict], translated: List[dict]) -> List[dict]:
    """Pair each script scene with its translated Kling prompt, clip duration and
    mood. Falls back to a deterministic prompt/mood for any scene the LLM
    translator did not cover, so every scene yields a clip plan entry."""
    fallback_prompts = translate_visuals_batch(script_scenes)
    plan = []
    for i, scene in enumerate(script_scenes):
        t = translated[i] if i < len(translated) else None
        card_duration = int(scene.get("duration_seconds") or _FALLBACK_DURATION_DEFAULT)
        if t:
            prompt = build_final_prompt(t)
            # Requested seconds; generate_video_clip snaps to the model's menu.
            clip_duration = kling_duration(t)
            mood = t.get("mood") or _scene_mood(scene)
        else:
            prompt = fallback_prompts[i]
            clip_duration = card_duration
            mood = _scene_mood(scene)
        plan.append({
            "scene_number": scene.get("scene_number", i + 1),
            "kling_prompt": prompt,
            "clip_duration": clip_duration,
            "card_duration": card_duration,
            "mood": mood,
        })
    return plan


async def _generate_clip_with_fallback(
    provider: str,
    prompt: str,
    duration: int,
    clip_path: str,
    scene_number: int,
    content_type: str,
    mood: str,
    aspect_ratio: str = "16:9",
) -> None:
    """Generate one raw clip (video bytes only, no audio) for the scene,
    writing it to ``clip_path``. Applies the per-provider fallback hierarchy:

    ``wan2``  (SIGNAL/PULSE): Wan2.1 → image-slide (Ken Burns) → colour card.
              NEVER Kling (cost model).
    ``kling`` (STORIES):      Kling  → Wan2.1 → image-slide (Ken Burns) → colour card.

    The clip written here is NOT yet the final scene clip — the caller is
    responsible for normalising resolution/fps and muxing the scene audio.
    Cost is logged here so the logged provider reflects whichever tier actually
    produced the bytes (e.g. a Kling failure served by Wan2.1 logs "wan2").
    """
    if provider == "wan2":
        # --- SIGNAL / PULSE path (Wan2.1 → slide → colour card; never Kling) ---
        try:
            data = await _wan_client.generate_clip(
                prompt=prompt, duration_seconds=duration,
            )
            Path(clip_path).write_bytes(data)
            log_generation_cost("wan2", content_type, scene_number, False)
            return
        except Wan2GenerationError as exc:
            logger.warning(
                "Wan2.1 failed for scene %d (%s); trying image-slide fallback.",
                scene_number, exc,
            )

        # Slide tier: fal FLUX image rendered as Ken Burns mp4.
        try:
            await generate_slide_clip(prompt, duration, clip_path, aspect_ratio=aspect_ratio)
            log_generation_cost("slide", content_type, scene_number, True)
            return
        except SlideClipError as exc:
            logger.warning(
                "Image-slide fallback failed for scene %d (%s); using colour card.",
                scene_number, exc,
            )

        # Colour card — last resort; no motion but always succeeds.
        generate_fallback_card(mood, duration, clip_path)
        log_generation_cost("colour_card", content_type, scene_number, True)
        return

    if provider == "kling":
        # --- STORIES path (Kling → Wan2.1 → slide → colour card) ---
        try:
            data = await generate_video_clip(
                prompt, duration=duration, aspect_ratio=aspect_ratio,
            )
            Path(clip_path).write_bytes(data)
            log_generation_cost("kling", content_type, scene_number, False)
            return
        except Exception as exc:
            # STORIES quality matters — try Wan2.1 before degrading further.
            logger.warning(
                "Kling failed for scene %d (%s); falling back to Wan2.1.", scene_number, exc,
            )

        try:
            data = await _wan_client.generate_clip(
                prompt=prompt, duration_seconds=duration,
            )
            Path(clip_path).write_bytes(data)
            log_generation_cost("wan2", content_type, scene_number, True)
            return
        except Wan2GenerationError as exc:
            logger.warning(
                "Wan2.1 fallback failed for scene %d (%s); trying image-slide.",
                scene_number, exc,
            )

        # Slide tier: fal FLUX image rendered as Ken Burns mp4.
        try:
            await generate_slide_clip(prompt, duration, clip_path, aspect_ratio=aspect_ratio)
            log_generation_cost("slide", content_type, scene_number, True)
            return
        except SlideClipError as exc:
            logger.warning(
                "Image-slide fallback failed for scene %d (%s); using colour card.",
                scene_number, exc,
            )

        # Colour card — last resort.
        generate_fallback_card(mood, duration, clip_path)
        log_generation_cost("colour_card", content_type, scene_number, True)
        return

    raise ValueError(f"Unknown provider: {provider!r}")


def _normalize_and_fit_clip(
    raw_clip_path: str,
    audio_path: str,
    narration_duration_s: float,
    out_path: str,
) -> None:
    """Normalize a raw video clip to the standard output format, fit it to the
    narration duration, and mux the scene audio as the audio track.

    Fitting strategy:
      - If the raw clip is SHORTER than the narration, ``-stream_loop -1``
        loops it until the audio ends (``-shortest`` trims to audio length).
      - If the raw clip is LONGER, it is trimmed to the narration duration.

    Normalisation filter applied to every clip regardless of source:
      scale={W}:{H}:force_original_aspect_ratio=decrease,
      pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,
      setsar=1,
      fps={FPS},
      format={PIX_FMT}

    Using force_original_aspect_ratio=decrease + pad keeps aspect-ratio intact
    and letter/pillar-boxes any off-ratio source (e.g. a 9:16 Kling clip or a
    4:3 Nova Canvas slide). setsar=1 fixes the sample-aspect-ratio so the
    concat-demuxer sees identical stream headers on every clip.

    All per-scene clips share the same codec settings (libx264 / AAC 192k) so
    the final concat-demuxer pass is a lossless stream copy.
    """
    vf = (
        f"scale={_OUT_WIDTH}:{_OUT_HEIGHT}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={_OUT_WIDTH}:{_OUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2,"
        f"setsar=1,"
        f"fps={_OUT_FPS},"
        f"format={_OUT_PIX_FMT}"
    )
    # duration_s rounded UP to the nearest whole second ensures the video clip
    # is never shorter than the audio (which is already narration_duration_s).
    target_s = math.ceil(narration_duration_s)

    _run_ffmpeg([
        "ffmpeg", "-y",
        # -stream_loop -1: infinite loop of the raw clip — trimmed by -t.
        # If the raw clip is already long enough, FFmpeg just stops reading once
        # -t is reached; there is no penalty for looping a long clip.
        "-stream_loop", "-1",
        "-i", raw_clip_path,
        "-i", audio_path,
        "-t", str(target_s),
        "-vf", vf,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264", "-crf", "20", "-preset", "medium",
        "-r", str(_OUT_FPS),
        "-c:a", "aac", "-b:a", "192k",
        # -shortest: the audio is authoritative — trim video to match it exactly.
        # Combined with -t (the ceiling), this ensures the scene clip is as long
        # as the narration and never longer.
        "-shortest",
        out_path,
    ])


async def assemble_video(
    scenes: List[dict],          # from the script tool output
    narration_text: str,         # full narration text (used only as translator hint)
    language_code: str,          # for voice routing
    output_s3_key: str,          # where to upload the final MP4
    content_type: str,           # 'signal' or 'stories'
    *,
    topic_name: str = "",        # passed to the visual translator
    on_progress: ProgressCb = None,
) -> str:
    """
    Full pipeline: translate → per-scene narration → generate + fit clips → stitch → upload.
    Returns the S3 key of the assembled video.

    Per-scene assembly flow (Section 4 rewrite)
    --------------------------------------------
    1. Translate all scenes to concrete video prompts (visual_translator).
    2. Synthesize per-scene narration audio (ElevenLabs → Polly fallback) via
       ``synthesize_scene_narrations``; each scene gets a real ``duration_ms``.
    3. For each scene (sequentially, respecting the semaphore):
       a. Generate a raw clip via the provider fallback chain. The target
          ``clip_duration`` fed to the video model is taken from the translated
          plan (model-snapped), not from the narration (which might be shorter).
       b. Normalize the raw clip (scale / SAR / fps / pix_fmt) AND fit it to the
          scene's narration duration (loop if clip < narration; trim if clip >
          narration), then mux the scene narration as audio.
       c. The resulting per-scene clip is complete: correct duration, codec, and
          audio. No further processing needed.
    4. Concat all per-scene clips via the concat-demuxer with ``-c copy``
       (lossless — all clips are already uniform). Upload to S3.

    Resilience guarantees:
    - A clip that fails to generate is replaced by a mood-coloured fallback card
      (→ slide → colour card). The whole assembly is NEVER aborted for one failed clip.
    - Temp files are cleaned up only on success. On failure (e.g. S3 upload) the
      temp directory is kept and its path logged for debugging.
    - ``on_progress(patch: dict)`` is called after every clip (not batched) and at
      each stage boundary; it may be sync or async.

    Signature is unchanged from the pre-Section-4 version so all existing callers
    (generate_long_video in video_job.py, generate_film in stories/generator.py)
    require no edits.
    """
    _check_ffmpeg()

    work_dir = Path(tempfile.mkdtemp(prefix=f"{content_type}_assembly_"))
    total = len(scenes)
    succeeded = False
    try:
        # Step 1 — translate all scenes to concrete video prompts (Prompt 2).
        target_duration = sum(
            int(s.get("duration_seconds") or _FALLBACK_DURATION_DEFAULT) for s in scenes
        )
        translated = await translate_scenes(
            topic=topic_name,
            narration_script=narration_text,
            total_scenes=total,
            target_duration_seconds=target_duration,
        )
        plan = _build_clip_plan(scenes, translated)

        await _emit(on_progress, {
            "total_scenes": total,
            "clips_generated": 0,
            "narration_ready": False,
            "assembly_started": False,
            "current_stage": "narration",
        })

        # Step 2 — synthesize per-scene narration in the executor (blocking TTS
        # calls should not block the event loop). Each scene gets its own mp3 and
        # a real duration_ms that drives clip fitting in step 3.
        loop = asyncio.get_event_loop()
        scene_audio_list: List[dict] = await loop.run_in_executor(
            None,
            synthesize_scene_narrations,
            scenes, language_code, str(work_dir),
        )
        # Index by scene_number for O(1) lookup.
        scene_audio_by_num: dict[int, dict] = {
            e["scene_number"]: e for e in scene_audio_list
        }

        await _emit(on_progress, {
            "narration_ready": True,
            "assembly_started": True,
            "current_stage": "generating_clips",
        })

        # Step 3 — per-scene clip generation + normalise + mux.
        # Clips are generated sequentially here because:
        #   (a) FFmpeg normalisation is CPU-bound, and
        #   (b) the semaphore already throttles concurrent model calls.
        # If parallelism is needed in the future, move the semaphore into this loop.
        provider = get_provider(content_type)
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_KLING_CALLS)
        done_lock = asyncio.Lock()
        clips_done = 0

        # Final per-scene clip paths (already normalised + audio-muxed).
        finished_clip_paths: List[str] = []

        async def process_one_scene(entry: dict) -> str:
            """Generate, normalise, fit, and mux one scene clip. Returns the
            path of the finished clip. Never raises — falls back to colour card."""
            nonlocal clips_done
            scene_number  = entry["scene_number"]
            audio_info    = scene_audio_by_num.get(scene_number)

            if audio_info is None:
                # Fallback: create a silence entry for any scene the audio index
                # is missing (should not happen, but defensive).
                logger.warning(
                    "No audio entry for scene %d — treating as silent.", scene_number
                )
                narration_duration_s = _FALLBACK_DURATION_DEFAULT
                audio_path = None
            else:
                narration_duration_s = audio_info["duration_ms"] / 1000.0
                audio_path = audio_info["audio_path"]

            # Paths for the raw clip (from model/fallback) and the finished clip.
            raw_clip_path     = str(work_dir / f"raw_{scene_number:04d}.mp4")
            finished_clip_path = str(work_dir / f"scene_{scene_number:04d}.mp4")

            async with semaphore:
                try:
                    await _generate_clip_with_fallback(
                        provider=provider,
                        prompt=entry["kling_prompt"],
                        duration=entry["clip_duration"],
                        clip_path=raw_clip_path,
                        scene_number=scene_number,
                        content_type=content_type,
                        mood=entry["mood"],
                    )
                except Exception as exc:
                    # Unexpected error in the fallback chain — degrade to colour card
                    # so the rest of the assembly can still proceed.
                    logger.warning(
                        "Clip generation entirely unexpected failure scene %d: %s; "
                        "using colour card.", scene_number, exc,
                    )
                    generate_fallback_card(
                        entry["mood"], int(math.ceil(narration_duration_s)), raw_clip_path
                    )
                    log_generation_cost("colour_card", content_type, scene_number, True)

            # Normalise + fit + mux audio. If audio_path is missing (silence
            # fallback path above), synthesise silence to a temp file so the
            # output always has an audio track.
            if audio_path is None or not Path(audio_path).exists():
                # Emergency: generate silence via lavfi anullsrc.
                silence_path = str(work_dir / f"silence_{scene_number:04d}.mp3")
                _run_ffmpeg([
                    "ffmpeg", "-y",
                    "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=mono",
                    "-t", str(int(math.ceil(narration_duration_s))),
                    "-q:a", "9", "-acodec", "libmp3lame",
                    silence_path,
                ])
                audio_path = silence_path

            try:
                _normalize_and_fit_clip(
                    raw_clip_path, audio_path, narration_duration_s, finished_clip_path
                )
            except Exception as exc:
                # Normalisation failure: write a colour card directly to the
                # finished-clip slot so the concat manifest remains complete.
                logger.error(
                    "Normalisation failed for scene %d (%s); substituting colour card.",
                    scene_number, exc,
                )
                try:
                    generate_fallback_card(
                        entry["mood"], int(math.ceil(narration_duration_s)),
                        finished_clip_path,
                    )
                    # Mux the already-generated audio onto the colour card.
                    _run_ffmpeg([
                        "ffmpeg", "-y",
                        "-i", finished_clip_path,
                        "-i", audio_path,
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-c:v", "libx264", "-c:a", "aac", "-b:a", "192k",
                        "-shortest",
                        finished_clip_path + ".muxed.mp4",
                    ])
                    import os
                    os.replace(finished_clip_path + ".muxed.mp4", finished_clip_path)
                except Exception as card_exc:
                    logger.error(
                        "Colour-card fallback also failed for scene %d (%s).",
                        scene_number, card_exc,
                    )

            # Update progress counter after every clip.
            async with done_lock:
                clips_done += 1
                current = clips_done
            await _emit(on_progress, {"clips_generated": current})
            return finished_clip_path

        # Run all scene tasks. We use asyncio.gather so progress callbacks fire
        # concurrently (the semaphore keeps actual model calls bounded).
        finished_paths_unordered = await asyncio.gather(
            *(process_one_scene(e) for e in plan)
        )
        # asyncio.gather preserves input order — align with plan.
        finished_clip_paths = list(finished_paths_unordered)

        await _emit(on_progress, {"current_stage": "assembling"})

        # Step 4 — concat all per-scene clips (already uniform format) using the
        # concat-demuxer with stream copy (no re-encode, no glitch).
        concat_path = work_dir / "concat.txt"
        write_concat_manifest(finished_clip_paths, str(concat_path))

        final_path = work_dir / "final.mp4"
        _run_ffmpeg([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_path),
            # Stream copy: all clips share identical codec/format headers so
            # no re-encode is needed.  -movflags +faststart puts the moov atom
            # at the front of the MP4 for streaming-friendly playback.
            "-c", "copy",
            "-movflags", "+faststart",
            str(final_path),
        ])

        # Step 5 — upload and (only then) clean up.
        await _emit(on_progress, {"current_stage": "uploading"})
        store = AssetStore()
        with open(final_path, "rb") as f:
            store._upload(output_s3_key, f, "video/mp4")

        succeeded = True
        await _emit(on_progress, {"current_stage": "complete"})
        logger.info(
            "[%s] assembled %d scenes → s3://%s", content_type, total, output_s3_key
        )
        return output_s3_key

    finally:
        if succeeded:
            shutil.rmtree(work_dir, ignore_errors=True)
        else:
            # Keep temp files on failure — they are needed for debugging.
            logger.error(
                "[%s] assembly failed — keeping temp files for debug at %s",
                content_type, work_dir,
            )
