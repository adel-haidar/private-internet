import os
import json
import math
import logging
import tempfile
import subprocess
from typing import List

from private_internet.content.video_generator import ScriptSection

logger = logging.getLogger(__name__)

FPS = 24
WIDTH = 1280
HEIGHT = 720


class VideoAssemblyError(Exception):
    """Raised when an FFmpeg step fails."""


def _run_ffmpeg(args: List[str]) -> None:
    try:
        subprocess.run(args, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
        logger.error(f"FFmpeg failed: {' '.join(args)}\n{stderr}")
        raise VideoAssemblyError(f"FFmpeg command failed: {stderr[-2000:]}") from e


class VideoAssembler:
    """Assembles per-section visuals + narration audio into a single MP4.

    Each visual is either a generated video clip (.mp4 — looped under the
    narration) or a still image (.png — Ken Burns zoom), so a fal-video section
    and a slide-fallback section can coexist in one video."""

    def assemble(
        self,
        sections: List[ScriptSection],
        image_paths: List[str],   # one visual per section: .mp4 clip OR .png still
        audio_paths: List[str],   # one mp3 per section
        output_path: str,
    ) -> int:
        """
        Build one clip per section, concatenate them, write `output_path`.
        Returns total duration in seconds.
        """
        if not (len(sections) == len(image_paths) == len(audio_paths)):
            raise VideoAssemblyError("sections, image_paths and audio_paths must have equal length")

        with tempfile.TemporaryDirectory(prefix="video_assembly_") as temp_dir:
            clip_paths = []
            for i, (visual_path, audio_path) in enumerate(zip(image_paths, audio_paths)):
                clip_path = os.path.join(temp_dir, f"section_{i}.mp4")
                if visual_path.lower().endswith(".mp4"):
                    self._build_video_clip(visual_path, audio_path, clip_path)
                else:
                    self._build_kenburns_clip(visual_path, audio_path, clip_path)
                clip_paths.append(clip_path)

            concat_file = os.path.join(temp_dir, "concat.txt")
            with open(concat_file, "w") as f:
                for clip_path in clip_paths:
                    f.write(f"file '{clip_path}'\n")

            _run_ffmpeg([
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-movflags", "+faststart",
                output_path,
            ])

            return int(round(self._probe_duration_s(output_path)))

    def _build_kenburns_clip(self, image_path: str, audio_path: str, clip_path: str) -> None:
        """Still image → Ken Burns zoom for the narration's duration."""
        audio_duration_s = self._probe_duration_s(audio_path)
        duration_frames = max(1, math.ceil(audio_duration_s * FPS))
        zoompan = (
            f"scale={WIDTH}:{HEIGHT},"
            f"zoompan=z='if(lte(zoom,1.0),1.5,max(1.001,zoom-0.0015))'"
            f":d={duration_frames}:s={WIDTH}x{HEIGHT}:fps={FPS},"
            f"format=yuv420p"
        )
        _run_ffmpeg([
            "ffmpeg", "-y",
            "-loop", "1", "-i", image_path,
            "-i", audio_path,
            "-vf", zoompan,
            "-c:v", "libx264",
            "-c:a", "aac",
            "-r", str(FPS),
            "-shortest",
            clip_path,
        ])

    def _build_video_clip(self, video_path: str, audio_path: str, clip_path: str) -> None:
        """Generated video clip → loop it under the narration for the audio's
        duration, dropping any source audio in favour of the narration. Output is
        normalised (size/fps/pix_fmt) so it concatenates with Ken Burns clips."""
        _run_ffmpeg([
            "ffmpeg", "-y",
            "-stream_loop", "-1", "-i", video_path,
            "-i", audio_path,
            "-vf", f"scale={WIDTH}:{HEIGHT},setsar=1,fps={FPS},format=yuv420p",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264",
            "-c:a", "aac",
            "-shortest",
            clip_path,
        ])

    @staticmethod
    def _probe_duration_s(media_path: str) -> float:
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "json",
                    media_path,
                ],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode("utf-8", errors="replace") if e.stderr else ""
            raise VideoAssemblyError(f"ffprobe failed for {media_path}: {stderr[-500:]}") from e
        return float(json.loads(result.stdout)["format"]["duration"])
