import json
import logging
import subprocess

import boto3
from botocore.exceptions import ClientError

from private_internet.config import get_settings

logger = logging.getLogger(__name__)

# Known voices that aren't available on the neural engine — start them on
# standard. The runtime fallback below covers any voice not listed here.
NON_NEURAL_VOICES = {"Maxim", "Tatyana"}


class PollyEngine:
    """Synthesizes narration audio per script section via Amazon Polly."""

    def __init__(self):
        settings = get_settings()
        self.polly = boto3.client("polly", region_name=settings.aws_region)

    def synthesize_section(
        self,
        text: str,
        voice_id: str,
        language_code: str,
        output_path: str,
    ) -> int:
        """
        Synthesize `text` to an mp3 at `output_path`.
        Returns the audio duration in milliseconds.
        """
        preferred = "standard" if voice_id in NON_NEURAL_VOICES else "neural"
        alternate = "neural" if preferred == "standard" else "standard"
        try:
            response = self._synthesize(text, voice_id, language_code, preferred)
        except ClientError as exc:
            # Polly voices vary in engine support per locale ("This voice does not
            # support the selected engine: ..."). Retry on the other engine rather
            # than failing the whole video.
            if "does not support the selected engine" in str(exc):
                logger.warning(
                    f"Voice {voice_id} does not support the {preferred} engine; "
                    f"retrying on {alternate}."
                )
                response = self._synthesize(text, voice_id, language_code, alternate)
            else:
                raise
        with open(output_path, "wb") as f:
            f.write(response["AudioStream"].read())
        return self._probe_duration_ms(output_path)

    def _synthesize(self, text: str, voice_id: str, language_code: str, engine: str):
        return self.polly.synthesize_speech(
            Engine=engine,
            OutputFormat="mp3",
            VoiceId=voice_id,
            LanguageCode=language_code,
            TextType="text",
            Text=text,
        )

    @staticmethod
    def _probe_duration_ms(audio_path: str) -> int:
        """Read the mp3 duration with ffprobe (ships with ffmpeg)."""
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                audio_path,
            ],
            check=True,
            capture_output=True,
        )
        duration_s = float(json.loads(result.stdout)["format"]["duration"])
        return int(duration_s * 1000)

    def get_total_duration(self, section_durations: list[int]) -> int:
        """Sum of all section durations in ms."""
        return sum(section_durations)
