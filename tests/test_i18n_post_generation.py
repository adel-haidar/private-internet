"""Tests for language-aware post and topic generation (Bug C).

Verifies:
- PostTextGenerator.generate() injects the language directive into the system prompt
- generate_posts_batch resolves language once and passes it down
- topic_intelligence._label_keyword_set includes language directive in the Bedrock prompt
- topic naming uses the user's language in extract_topic_candidates_clustered
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from private_internet.content.post_generator import PostTextGenerator


# ── Helpers ───────────────────────────────────────────────────────────────────

def _creator(slug="curious-mind"):
    return {
        "id": "c1",
        "slug": slug,
        "name": "Curious Mind",
        "style_prompt": "Write like a curious observer.",
        "topic_affinities": ["culture", "ideas"],
        "score": 0.7,
        "is_active": True,
    }


def _topic():
    return {
        "id": "t1",
        "name": "Japanese urban planning",
        "slug": "japanese-urban-planning",
        "keywords": ["urban", "tokyo", "city"],
        "weight": 0.8,
    }


def _valid_post_body():
    return " ".join(["word"] * 89 + ["end."])


def _tool_post(body=None):
    body = body or _valid_post_body()
    return {
        "format_chosen": "micro_story",
        "format_justification": "fits",
        "post_body": body,
        "word_count": len(body.split()),
        "opening_sentence": "Tokyo redesigned its streets.",
        "target_emotion": "curiosity",
    }


# ── PostTextGenerator: language directive ─────────────────────────────────────

class TestPostTextGeneratorLanguage:
    @pytest.mark.anyio
    async def test_japanese_directive_in_system_prompt(self):
        """When language_code='ja', the system prompt must contain the Japanese directive."""
        mock_converse = AsyncMock(return_value=(_tool_post(), {"inputTokens": 10, "outputTokens": 5}))
        with patch("private_internet.content.post_generator.converse_tool", new=mock_converse):
            generator = PostTextGenerator()
            await generator.generate(_topic(), _creator(), "informative", [], language_code="ja")

        kwargs = mock_converse.call_args.kwargs
        system_prompt = kwargs["system_prompt"]
        assert "Japanese" in system_prompt, (
            "System prompt must contain 'Japanese' for language_code='ja'"
        )
        assert "Not English unless" in system_prompt

    @pytest.mark.anyio
    async def test_english_directive_for_english(self):
        """For language_code='en', the directive references English."""
        mock_converse = AsyncMock(return_value=(_tool_post(), {}))
        with patch("private_internet.content.post_generator.converse_tool", new=mock_converse):
            generator = PostTextGenerator()
            await generator.generate(_topic(), _creator(), "informative", [], language_code="en")

        kwargs = mock_converse.call_args.kwargs
        assert "English" in kwargs["system_prompt"]

    @pytest.mark.anyio
    async def test_default_language_is_english(self):
        """Omitting language_code defaults to English."""
        mock_converse = AsyncMock(return_value=(_tool_post(), {}))
        with patch("private_internet.content.post_generator.converse_tool", new=mock_converse):
            generator = PostTextGenerator()
            await generator.generate(_topic(), _creator(), "informative", [])

        kwargs = mock_converse.call_args.kwargs
        assert "English" in kwargs["system_prompt"]

    @pytest.mark.anyio
    async def test_arabic_directive(self):
        mock_converse = AsyncMock(return_value=(_tool_post(), {}))
        with patch("private_internet.content.post_generator.converse_tool", new=mock_converse):
            generator = PostTextGenerator()
            await generator.generate(_topic(), _creator(), "informative", [], language_code="ar")

        kwargs = mock_converse.call_args.kwargs
        assert "Arabic" in kwargs["system_prompt"]


# ── generate_posts_batch: language resolution ─────────────────────────────────

class TestGeneratePostsBatchLanguage:
    @pytest.mark.anyio
    async def test_language_resolved_once_and_passed_down(self):
        """resolve_user_language must be called once; language_code must reach the generator."""
        from private_internet.content.jobs.post_job import generate_posts_batch
        from private_internet.content.post_generator import GeneratedPost

        topic = _topic()
        creator = _creator()

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.side_effect = [[topic], []]
        conn.cursor.return_value = cursor

        mock_selector = MagicMock()
        mock_selector.select_for_topic.return_value = creator
        mock_selector.select_tone.return_value = "informative"

        mock_gen = MagicMock()
        mock_gen.generate = AsyncMock(
            return_value=GeneratedPost(body=_valid_post_body(), referenced_urls=[], usage={})
        )
        mock_image_gen = MagicMock()
        mock_image_gen.generate_for_post = AsyncMock(side_effect=RuntimeError("no image"))

        with (
            patch("private_internet.content.jobs.post_job._connect", return_value=conn),
            patch("private_internet.content.jobs.post_job.CreatorSelector", return_value=mock_selector),
            patch("private_internet.content.jobs.post_job.PostTextGenerator", return_value=mock_gen),
            patch("private_internet.content.jobs.post_job.PostImageGenerator", return_value=mock_image_gen),
            patch("private_internet.content.jobs.post_job.AssetStore", return_value=MagicMock()),
            patch(
                "private_internet.content.jobs.post_job.resolve_user_language",
                return_value="ja",
            ) as mock_lang,
        ):
            result = await generate_posts_batch(count=1, user_id="user-jp-test")

        # Language resolved exactly once
        mock_lang.assert_called_once_with("user-jp-test")

        # The generate call received language_code='ja'
        gen_call_kwargs = mock_gen.generate.call_args.kwargs
        assert gen_call_kwargs.get("language_code") == "ja", (
            "generate() must receive language_code='ja'"
        )

        assert result["created"] == 1


# ── topic_intelligence: language-aware labelling ─────────────────────────────

class TestTopicLabellingLanguage:
    def test_label_keyword_set_includes_language_directive(self):
        """_label_keyword_set must inject the language name into the Bedrock prompt."""
        import json
        from private_internet.content.topic_intelligence import MCPMemoryReader

        reader = MCPMemoryReader()
        candidate = {
            "keywords": ["東京", "電車", "交通"],
            "kind": "cluster",
            "source_ids": ["m1"],
        }

        captured_system = []
        def fake_invoke(system_prompt, user_prompt):
            captured_system.append(system_prompt)
            return json.dumps({"name": "東京交通", "slug": "tokyo-traffic", "keywords": ["東京"]})

        with patch(
            "private_internet.content.topic_intelligence._invoke_bedrock_text",
            side_effect=fake_invoke,
        ):
            result = reader._label_keyword_set(candidate, language_code="ja")

        assert result is not None
        assert result.name == "東京交通"
        # The system prompt must contain the language directive
        assert captured_system, "Bedrock must have been called"
        assert "Japanese" in captured_system[0], (
            "System prompt must mention the target language"
        )
        assert "Not English unless" in captured_system[0]

    def test_label_keyword_set_english_is_default(self):
        """Without language_code, the English fallback applies."""
        import json
        from private_internet.content.topic_intelligence import MCPMemoryReader

        reader = MCPMemoryReader()
        candidate = {"keywords": ["machine", "learning", "model"], "kind": "cluster", "source_ids": []}
        captured = []

        def fake_invoke(system_prompt, user_prompt):
            captured.append(system_prompt)
            return json.dumps({"name": "Machine learning", "slug": "machine-learning", "keywords": ["ml"]})

        with patch(
            "private_internet.content.topic_intelligence._invoke_bedrock_text",
            side_effect=fake_invoke,
        ):
            result = reader._label_keyword_set(candidate)

        assert result is not None
        assert "English" in captured[0]

    @pytest.mark.anyio
    async def test_extract_topic_candidates_clustered_resolves_language(self):
        """extract_topic_candidates_clustered must call resolve_user_language and
        pass the code through to _label_keyword_set."""
        import json
        from private_internet.content.topic_intelligence import MCPMemoryReader, TopicCandidate

        uid = "user-lang-test"
        reader = MCPMemoryReader()
        candidate_sets = [{"keywords": ["tech", "ai"], "kind": "cluster", "source_ids": ["m1"]}]

        fake_topic = TopicCandidate("AI trends", "ai-trends", ["ai"], "mcp_memory", "m1")

        with (
            patch(
                "private_internet.content.topic_intelligence.build_keyword_candidates",
                return_value=candidate_sets,
            ),
            patch(
                "private_internet.content.topic_intelligence.resolve_user_language",
                return_value="de",
            ) as mock_lang,
            patch.object(reader, "_label_keyword_set", return_value=fake_topic) as mock_label,
        ):
            results = await reader.extract_topic_candidates_clustered(user_id=uid)

        mock_lang.assert_called_once_with(uid)
        # _label_keyword_set must receive language_code='de'
        assert mock_label.call_args.kwargs.get("language_code") == "de"
        assert len(results) == 1
