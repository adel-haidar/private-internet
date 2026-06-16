"""Tests for SIGNAL language-awareness: script generators must inject the correct
language directive into their system prompts, and video_job must thread the
resolved language_code through to the script generators and assemble_video.
"""

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from private_internet.content.video_generator import (
    VideoScriptGenerator,
    SceneScriptGenerator,
    SECTION_IDS,
    VideoScript,
    ScriptSection,
)
from private_internet.content.voice_config import get_voice_id, language_name, VOICE_MAP


# ── Helpers ────────────────────────────────────────────────────────────────────

def _creator():
    return {
        "id": str(uuid.uuid4()),
        "slug": "test-creator",
        "name": "Test Creator",
        "style_prompt": "Write in a calm, informative tone.",
        "polly_voice_id": "Joanna",
        "polly_language_code": "en-US",
    }


def _topic(name="Circular Economy"):
    return {"id": str(uuid.uuid4()), "name": name}


def _script_json():
    return json.dumps({
        "title": "Circular Economy",
        "description": "A look at circular economy principles.",
        "sections": [
            {"id": sid, "text": f"Narration for {sid}.", "image_prompt": f"Image for {sid}"}
            for sid in SECTION_IDS
        ],
    })


def _scene_tool_result(num_scenes=3):
    return {
        "title": "Test Video",
        "total_duration_seconds": num_scenes * 8,
        "scenes": [
            {
                "scene_number": i + 1,
                "narration_text": f"Scene {i + 1} narration.",
                "visual_description": f"Scene {i + 1} visual.",
                "duration_seconds": 8,
                "scene_type": "development",
            }
            for i in range(num_scenes)
        ],
    }


# ── voice_config ───────────────────────────────────────────────────────────────

class TestVoiceConfig:
    def test_language_name_japanese(self):
        assert language_name("ja") == "Japanese"

    def test_language_name_english(self):
        assert language_name("en") == "English"

    def test_language_name_unknown_falls_back_to_code(self):
        assert language_name("xx") == "xx"

    def test_get_voice_id_japanese_mapped(self):
        """Japanese must have a dedicated voice (not the English default)."""
        assert "ja" in VOICE_MAP
        assert get_voice_id("ja") == VOICE_MAP["ja"]

    def test_get_voice_id_english_unchanged(self):
        """English voice must remain exactly as before (no regression)."""
        assert get_voice_id("en") == VOICE_MAP["en"]

    def test_get_voice_id_unmapped_returns_default(self):
        """An unmapped code falls back to the English default voice."""
        default = get_voice_id("en")
        assert get_voice_id("zz") == default


# ── VideoScriptGenerator — language directive ──────────────────────────────────

class TestVideoScriptGeneratorLanguage:
    @pytest.mark.anyio
    async def test_japanese_directive_in_system_prompt(self):
        """When language_code='ja', the system prompt must contain the Japanese
        directive and NOT contain the old English-only hardcode."""
        mock_converse = AsyncMock(return_value=(_script_json(), {}))
        with patch(
            "private_internet.content.video_generator.converse_text",
            new=mock_converse,
        ):
            await VideoScriptGenerator().generate(
                _topic(), _creator(), [], language_code="ja"
            )

        system_prompt = mock_converse.call_args.kwargs["system_prompt"]
        assert "Japanese" in system_prompt, "Japanese directive missing from system prompt"
        assert "Not English unless Japanese is English" in system_prompt
        # Old hardcoded English-only directive must be gone.
        assert "write it ENTIRELY in English" not in system_prompt
        assert "ENTIRELY in English" not in system_prompt

    @pytest.mark.anyio
    async def test_english_directive_in_system_prompt(self):
        """When language_code='en', the system prompt must say English and not
        include a 'Not English unless…' clause (since English IS English)."""
        mock_converse = AsyncMock(return_value=(_script_json(), {}))
        with patch(
            "private_internet.content.video_generator.converse_text",
            new=mock_converse,
        ):
            await VideoScriptGenerator().generate(
                _topic(), _creator(), [], language_code="en"
            )

        system_prompt = mock_converse.call_args.kwargs["system_prompt"]
        # Directive present with the language name.
        assert "English" in system_prompt
        # The "Not English unless English is English" clause must still be there
        # (it reads correctly: true, English IS English, so not-a-contradiction).
        assert "Not English unless English is English" in system_prompt

    @pytest.mark.anyio
    async def test_default_language_is_english(self):
        """Calling generate() without language_code defaults to English (no regression)."""
        mock_converse = AsyncMock(return_value=(_script_json(), {}))
        with patch(
            "private_internet.content.video_generator.converse_text",
            new=mock_converse,
        ):
            await VideoScriptGenerator().generate(_topic(), _creator(), [])

        system_prompt = mock_converse.call_args.kwargs["system_prompt"]
        assert "English" in system_prompt

    @pytest.mark.anyio
    async def test_german_directive_in_system_prompt(self):
        mock_converse = AsyncMock(return_value=(_script_json(), {}))
        with patch(
            "private_internet.content.video_generator.converse_text",
            new=mock_converse,
        ):
            await VideoScriptGenerator().generate(
                _topic(), _creator(), [], language_code="de"
            )

        system_prompt = mock_converse.call_args.kwargs["system_prompt"]
        assert "German" in system_prompt
        assert "Not English unless German is English" in system_prompt


# ── SceneScriptGenerator — language directive ──────────────────────────────────

class TestSceneScriptGeneratorLanguage:
    @pytest.mark.anyio
    async def test_japanese_directive_in_system_prompt(self):
        """SceneScriptGenerator must inject the Japanese directive when language_code='ja'."""
        mock_converse = AsyncMock(return_value=(_scene_tool_result(), {}))
        with patch(
            "private_internet.content.video_generator.converse_tool",
            new=mock_converse,
        ):
            await SceneScriptGenerator().generate(
                _topic(), _creator(), [],
                duration_min=32, duration_max=48,
                language_code="ja",
            )

        system_prompt = mock_converse.call_args.kwargs["system_prompt"]
        assert "Japanese" in system_prompt
        assert "Not English unless Japanese is English" in system_prompt
        # Old hardcode must be gone.
        assert "ENTIRELY in English" not in system_prompt

    @pytest.mark.anyio
    async def test_english_directive_in_system_prompt(self):
        """English users get English directive; old hardcode form must not appear."""
        mock_converse = AsyncMock(return_value=(_scene_tool_result(), {}))
        with patch(
            "private_internet.content.video_generator.converse_tool",
            new=mock_converse,
        ):
            await SceneScriptGenerator().generate(
                _topic(), _creator(), [],
                duration_min=32, duration_max=48,
                language_code="en",
            )

        system_prompt = mock_converse.call_args.kwargs["system_prompt"]
        assert "English" in system_prompt
        # Must NOT contain the old literal string that was the bug.
        assert "ENTIRELY in English" not in system_prompt

    @pytest.mark.anyio
    async def test_default_language_is_english(self):
        mock_converse = AsyncMock(return_value=(_scene_tool_result(), {}))
        with patch(
            "private_internet.content.video_generator.converse_tool",
            new=mock_converse,
        ):
            await SceneScriptGenerator().generate(
                _topic(), _creator(), [],
                duration_min=32, duration_max=48,
            )

        system_prompt = mock_converse.call_args.kwargs["system_prompt"]
        assert "English" in system_prompt


# ── generate_video — language threading ───────────────────────────────────────

class TestGenerateVideoLanguageThreading:
    """generate_video() must call resolve_user_language and pass language_code
    to the script generator and to the ElevenLabs voice routing."""

    def _make_script(self):
        return VideoScript(
            title="Test Video",
            description="A test.",
            sections=[
                ScriptSection(
                    id=sid,
                    text=f"Text for {sid}.",
                    image_prompt=f"Image for {sid}.",
                )
                for sid in SECTION_IDS
            ],
        )

    @pytest.mark.anyio
    async def test_language_code_flows_to_script_generator(self):
        from private_internet.content.jobs.video_job import generate_video

        script = self._make_script()
        script_gen = MagicMock()
        script_gen.generate = AsyncMock(return_value=script)

        image_gen = MagicMock()
        image_gen.generate_for_section = AsyncMock(return_value=b"img")
        image_gen.generate_thumbnail = AsyncMock(return_value=b"thumb")

        polly = MagicMock()
        polly.synthesize_section.return_value = 5000

        assembler = MagicMock()
        assembler.assemble.return_value = 60

        asset_store = MagicMock()
        asset_store.upload_video.return_value = "https://cdn.example/v.mp4"
        asset_store.upload_thumbnail.return_value = "https://cdn.example/t.png"

        selector = MagicMock()
        selector.select_for_topic.return_value = _creator()

        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor

        base = "private_internet.content.jobs.video_job"
        patches = [
            patch(f"{base}._connect", return_value=conn),
            patch(f"{base}._select_topic", return_value=_topic()),
            patch(f"{base}._fetch_research", return_value=[]),
            patch(f"{base}.CreatorSelector", return_value=selector),
            patch(f"{base}.VideoScriptGenerator", return_value=script_gen),
            patch(f"{base}.VideoImageGenerator", return_value=image_gen),
            patch(f"{base}.get_tts_engine", return_value=polly),
            patch(f"{base}.get_settings", return_value=SimpleNamespace(video_backend="slides")),
            patch(f"{base}.VideoAssembler", return_value=assembler),
            patch(f"{base}.AssetStore", return_value=asset_store),
            patch(f"{base}.resolve_user_language", return_value="ja"),
            patch(f"{base}.shutil.rmtree"),
        ]

        for p in patches:
            p.start()
        try:
            await generate_video(user_id="test-user-id")
        finally:
            for p in patches:
                p.stop()

        # Script generator must receive language_code="ja"
        script_gen.generate.assert_awaited_once()
        call_kwargs = script_gen.generate.call_args.kwargs
        assert call_kwargs.get("language_code") == "ja", (
            f"Expected language_code='ja' in script generate() call; got {call_kwargs}"
        )

    @pytest.mark.anyio
    async def test_elevenlabs_voice_uses_resolved_language(self):
        """When TTS is ElevenLabs, voice_id must come from get_voice_id(language_code)."""
        from private_internet.content.jobs.video_job import generate_video
        from private_internet.content.elevenlabs_engine import ElevenLabsEngine

        script = self._make_script()
        script_gen = MagicMock()
        script_gen.generate = AsyncMock(return_value=script)

        image_gen = MagicMock()
        image_gen.generate_for_section = AsyncMock(return_value=b"img")
        image_gen.generate_thumbnail = AsyncMock(return_value=b"thumb")

        # Use a real ElevenLabsEngine-shaped mock (isinstance check must pass).
        eleven_engine = MagicMock(spec=ElevenLabsEngine)
        eleven_engine.synthesize_section.return_value = 5000

        assembler = MagicMock()
        assembler.assemble.return_value = 60

        asset_store = MagicMock()
        asset_store.upload_video.return_value = "https://cdn.example/v.mp4"
        asset_store.upload_thumbnail.return_value = "https://cdn.example/t.png"

        selector = MagicMock()
        selector.select_for_topic.return_value = _creator()

        conn = MagicMock()
        conn.cursor.return_value = MagicMock()

        base = "private_internet.content.jobs.video_job"
        patches = [
            patch(f"{base}._connect", return_value=conn),
            patch(f"{base}._select_topic", return_value=_topic()),
            patch(f"{base}._fetch_research", return_value=[]),
            patch(f"{base}.CreatorSelector", return_value=selector),
            patch(f"{base}.VideoScriptGenerator", return_value=script_gen),
            patch(f"{base}.VideoImageGenerator", return_value=image_gen),
            patch(f"{base}.get_tts_engine", return_value=eleven_engine),
            patch(f"{base}.get_settings", return_value=SimpleNamespace(video_backend="slides")),
            patch(f"{base}.VideoAssembler", return_value=assembler),
            patch(f"{base}.AssetStore", return_value=asset_store),
            patch(f"{base}.resolve_user_language", return_value="ja"),
            patch(f"{base}.shutil.rmtree"),
        ]

        for p in patches:
            p.start()
        try:
            await generate_video(user_id="test-user-id")
        finally:
            for p in patches:
                p.stop()

        # Every synthesize_section call must pass the Japanese voice id.
        expected_voice = get_voice_id("ja")
        for c in eleven_engine.synthesize_section.call_args_list:
            _, kwargs = c.args, c.kwargs
            # synthesize_section(text, voice_id, lang_code, path)
            actual_voice = c.args[1] if len(c.args) > 1 else kwargs.get("voice_id")
            assert actual_voice == expected_voice, (
                f"Expected ElevenLabs voice_id={expected_voice!r} for 'ja'; "
                f"got {actual_voice!r}"
            )


# ── generate_long_video — language threading ──────────────────────────────────

class TestGenerateLongVideoLanguageThreading:
    """generate_long_video() must pass language_code to SceneScriptGenerator
    and to assemble_video."""

    @pytest.mark.anyio
    async def test_language_code_flows_to_scene_script_and_assembler(self):
        from private_internet.content.jobs.video_job import generate_long_video

        mock_scene_gen = MagicMock()
        mock_script = MagicMock()
        mock_script.scenes = [{"scene_number": 1, "narration_text": "Hello.", "duration_seconds": 8}]
        mock_script.narration_text = "Hello."
        mock_script.title = "Test"
        mock_script.total_duration_seconds = 40
        mock_scene_gen.generate = AsyncMock(return_value=mock_script)

        asset_store_inst = MagicMock()
        asset_store_inst.cdn_base = "https://cdn.example"

        conn = MagicMock()
        conn.cursor.return_value = MagicMock()

        captured_assemble_calls = []

        async def fake_assemble_video(**kwargs):
            captured_assemble_calls.append(kwargs)

        base = "private_internet.content.jobs.video_job"
        patches = [
            patch(f"{base}._connect", return_value=conn),
            patch(f"{base}._select_topic", return_value=_topic()),
            patch(f"{base}._fetch_research", return_value=[]),
            patch(f"{base}.CreatorSelector", return_value=MagicMock(
                select_for_topic=MagicMock(return_value=_creator())
            )),
            patch(f"{base}.SceneScriptGenerator", return_value=mock_scene_gen),
            patch(f"{base}.assemble_video", side_effect=fake_assemble_video),
            patch(f"{base}.AssetStore", return_value=asset_store_inst),
            patch(f"{base}.resolve_user_language", return_value="ja"),
        ]

        for p in patches:
            p.start()
        try:
            await generate_long_video(user_id="test-user-id", duration_band="short")
        finally:
            for p in patches:
                p.stop()

        # SceneScriptGenerator must receive language_code="ja"
        gen_kwargs = mock_scene_gen.generate.call_args.kwargs
        assert gen_kwargs.get("language_code") == "ja", (
            f"Expected language_code='ja' in SceneScriptGenerator.generate(); "
            f"got {gen_kwargs}"
        )

        # assemble_video must receive language_code="ja"
        assert len(captured_assemble_calls) == 1
        assert captured_assemble_calls[0]["language_code"] == "ja", (
            f"Expected language_code='ja' in assemble_video(); "
            f"got {captured_assemble_calls[0].get('language_code')!r}"
        )
