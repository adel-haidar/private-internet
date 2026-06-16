"""Unit tests for the per-user persona generation pipeline (Bug B).

Tests cover:
- generate_personas_for_user: DB isolation, idempotency, fallback personas
- persona_job: retirement logic, spawn threshold
- creator_selector: user_id scoping in DB query, tone fallback chain
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from private_internet.content.persona_generator import (
    _build_fallback_personas,
    _FALLBACK_PERSONA_TEMPLATES,
)
from private_internet.content.jobs.persona_job import (
    _RETIREMENT_INTERACTION_RATE,
    _MIN_POSTS_BEFORE_RETIREMENT,
    _SPAWN_TOPIC_THRESHOLD,
)


# ── Fallback personas ─────────────────────────────────────────────────────────

class TestBuildFallbackPersonas:
    def test_returns_correct_count(self):
        personas = _build_fallback_personas("en", "test-user-x")
        assert len(personas) == len(_FALLBACK_PERSONA_TEMPLATES)

    def test_slugs_are_unique_and_user_scoped(self):
        uid1 = "user-aaa"
        uid2 = "user-bbb"
        p1 = _build_fallback_personas("en", uid1)
        p2 = _build_fallback_personas("en", uid2)
        slugs1 = {p["slug"] for p in p1}
        slugs2 = {p["slug"] for p in p2}
        assert slugs1.isdisjoint(slugs2), "different users must get distinct slugs"

    def test_language_directive_in_style_prompt(self):
        personas = _build_fallback_personas("ja", "user-jp")
        for p in personas:
            assert "Japanese" in p["style_prompt"], (
                "Japanese language directive must appear in style_prompt"
            )

    def test_english_fallback_no_spurious_directive(self):
        personas = _build_fallback_personas("en", "user-en")
        for p in personas:
            assert "English" in p["style_prompt"]

    def test_required_keys_present(self):
        required = {"slug", "name", "bio", "style_prompt",
                    "topic_affinities", "valid_tones"}
        for p in _build_fallback_personas("en", "user-1"):
            missing = required - p.keys()
            assert not missing, f"persona missing keys: {missing}"


# ── generate_personas_for_user ────────────────────────────────────────────────

class TestGeneratePersonasForUser:
    @pytest.mark.anyio
    async def test_uses_fallback_when_brain_is_empty(self):
        """Empty topic list → fallback personas inserted."""
        uid = str(uuid.uuid4())
        with (
            patch(
                "private_internet.content.persona_generator.resolve_user_language",
                return_value="en",
            ),
            patch(
                "private_internet.content.persona_generator._fetch_user_top_topics",
                return_value=[],
            ),
            patch(
                "private_internet.content.persona_generator._existing_user_slugs",
                return_value=set(),
            ),
            patch(
                "private_internet.content.persona_generator._insert_persona"
            ) as mock_insert,
        ):
            from private_internet.content.persona_generator import generate_personas_for_user
            n = await generate_personas_for_user(uid)

        assert n == len(_FALLBACK_PERSONA_TEMPLATES)
        assert mock_insert.call_count == len(_FALLBACK_PERSONA_TEMPLATES)
        # Every inserted persona must carry the user_id
        for call in mock_insert.call_args_list:
            assert call.args[0] == uid

    @pytest.mark.anyio
    async def test_idempotent_skips_existing_slugs(self):
        """Slugs already in the DB for this user must be skipped."""
        uid = str(uuid.uuid4())
        fallbacks = _build_fallback_personas("en", uid)
        existing = {fallbacks[0]["slug"]}  # pretend first slug already exists

        with (
            patch(
                "private_internet.content.persona_generator.resolve_user_language",
                return_value="en",
            ),
            patch(
                "private_internet.content.persona_generator._fetch_user_top_topics",
                return_value=[],
            ),
            patch(
                "private_internet.content.persona_generator._existing_user_slugs",
                return_value=existing,
            ),
            patch(
                "private_internet.content.persona_generator._insert_persona"
            ) as mock_insert,
        ):
            from private_internet.content.persona_generator import generate_personas_for_user
            n = await generate_personas_for_user(uid)

        assert n == len(_FALLBACK_PERSONA_TEMPLATES) - 1
        assert mock_insert.call_count == len(_FALLBACK_PERSONA_TEMPLATES) - 1

    @pytest.mark.anyio
    async def test_uses_bedrock_when_brain_has_topics(self):
        """When the brain has topics, Bedrock is called; on success those are used."""
        uid = str(uuid.uuid4())
        topics = [{"name": "Machine learning", "keywords": ["ml", "model"], "weight": 0.9}]
        bedrock_personas = [
            {
                "slug": f"ml-guru-{uid[:4]}",
                "name": "ML Guru",
                "bio": "ML expert.",
                "style_prompt": "Write precisely.",
                "polly_voice_id": "Joanna",
                "polly_language_code": "en-US",
                "topic_affinities": ["ml", "AI"],
                "valid_tones": ["informative"],
            }
        ]

        with (
            patch(
                "private_internet.content.persona_generator.resolve_user_language",
                return_value="en",
            ),
            patch(
                "private_internet.content.persona_generator._fetch_user_top_topics",
                return_value=topics,
            ),
            patch(
                "private_internet.content.persona_generator._existing_user_slugs",
                return_value=set(),
            ),
            patch(
                "private_internet.content.persona_generator._generate_personas_via_bedrock",
                new=AsyncMock(return_value=bedrock_personas),
            ),
            patch(
                "private_internet.content.persona_generator._insert_persona"
            ) as mock_insert,
        ):
            from private_internet.content.persona_generator import generate_personas_for_user
            n = await generate_personas_for_user(uid)

        assert n == 1
        assert mock_insert.call_args.args[1]["slug"] == bedrock_personas[0]["slug"]

    @pytest.mark.anyio
    async def test_falls_back_when_bedrock_fails(self):
        """If Bedrock persona generation fails, fallback personas are still inserted."""
        uid = str(uuid.uuid4())
        topics = [{"name": "Robotics", "keywords": ["robot"], "weight": 0.8}]

        with (
            patch(
                "private_internet.content.persona_generator.resolve_user_language",
                return_value="en",
            ),
            patch(
                "private_internet.content.persona_generator._fetch_user_top_topics",
                return_value=topics,
            ),
            patch(
                "private_internet.content.persona_generator._existing_user_slugs",
                return_value=set(),
            ),
            patch(
                "private_internet.content.persona_generator._generate_personas_via_bedrock",
                new=AsyncMock(return_value=[]),  # simulate bedrock returning nothing
            ),
            patch(
                "private_internet.content.persona_generator._insert_persona"
            ) as mock_insert,
        ):
            from private_internet.content.persona_generator import generate_personas_for_user
            n = await generate_personas_for_user(uid)

        # Falls back to the template set
        assert n == len(_FALLBACK_PERSONA_TEMPLATES)
        assert mock_insert.call_count == len(_FALLBACK_PERSONA_TEMPLATES)

    @pytest.mark.anyio
    async def test_user_id_asserted(self):
        """Passing None must raise immediately."""
        with pytest.raises(AssertionError):
            from private_internet.content.persona_generator import generate_personas_for_user
            await generate_personas_for_user(None)


# ── persona_job: retirement / spawn logic ────────────────────────────────────

class TestPersonaEvolutionJob:
    @pytest.mark.anyio
    async def test_retires_stale_persona(self):
        """A persona with >= MIN_POSTS and low interaction rate should be retired."""
        uid = str(uuid.uuid4())
        stale_creator_id = str(uuid.uuid4())

        # Engagement: many posts, zero interactions → retired
        engagement = [
            {
                "creator_id": stale_creator_id,
                "slug": "stale-persona",
                "post_count": _MIN_POSTS_BEFORE_RETIREMENT,
                "interaction_count": 0,
                "interaction_rate": 0.0,
            }
        ]

        conn = MagicMock()

        with (
            patch(
                "private_internet.content.jobs.persona_job._connect",
                return_value=conn,
            ),
            patch(
                "private_internet.content.jobs.persona_job._get_user_persona_engagement",
                return_value=engagement,
            ),
            patch(
                "private_internet.content.jobs.persona_job._retire_persona"
            ) as mock_retire,
            patch(
                "private_internet.content.jobs.persona_job._count_active_user_personas",
                return_value=2,
            ),
            patch(
                "private_internet.content.jobs.persona_job._uncovered_topic_count",
                return_value=0,  # below threshold → no spawn
            ),
            patch(
                "private_internet.content.jobs.persona_job.generate_personas_for_user",
                new=AsyncMock(return_value=0),
            ),
        ):
            from private_internet.content.jobs.persona_job import run_persona_evolution_job
            result = await run_persona_evolution_job(user_id=uid)

        mock_retire.assert_called_once_with(conn, stale_creator_id, uid, "stale-persona")
        assert result["retired"] == 1
        assert result["spawned"] == 0

    @pytest.mark.anyio
    async def test_does_not_retire_young_persona(self):
        """A persona with < MIN_POSTS must NOT be retired regardless of interactions."""
        uid = str(uuid.uuid4())
        engagement = [
            {
                "creator_id": str(uuid.uuid4()),
                "slug": "fresh-persona",
                "post_count": _MIN_POSTS_BEFORE_RETIREMENT - 1,
                "interaction_count": 0,
                "interaction_rate": 0.0,
            }
        ]

        conn = MagicMock()
        with (
            patch("private_internet.content.jobs.persona_job._connect", return_value=conn),
            patch(
                "private_internet.content.jobs.persona_job._get_user_persona_engagement",
                return_value=engagement,
            ),
            patch("private_internet.content.jobs.persona_job._retire_persona") as mock_retire,
            patch(
                "private_internet.content.jobs.persona_job._count_active_user_personas",
                return_value=1,
            ),
            patch(
                "private_internet.content.jobs.persona_job._uncovered_topic_count",
                return_value=0,
            ),
            patch(
                "private_internet.content.jobs.persona_job.generate_personas_for_user",
                new=AsyncMock(return_value=0),
            ),
        ):
            from private_internet.content.jobs.persona_job import run_persona_evolution_job
            result = await run_persona_evolution_job(user_id=uid)

        mock_retire.assert_not_called()
        assert result["retired"] == 0

    @pytest.mark.anyio
    async def test_spawns_when_uncovered_topics_above_threshold(self):
        """When uncovered topics >= threshold and cap not reached, spawn is triggered."""
        uid = str(uuid.uuid4())

        conn = MagicMock()
        with (
            patch("private_internet.content.jobs.persona_job._connect", return_value=conn),
            patch(
                "private_internet.content.jobs.persona_job._get_user_persona_engagement",
                return_value=[],
            ),
            patch(
                "private_internet.content.jobs.persona_job._count_active_user_personas",
                return_value=2,
            ),
            patch(
                "private_internet.content.jobs.persona_job._uncovered_topic_count",
                return_value=_SPAWN_TOPIC_THRESHOLD,
            ),
            patch(
                "private_internet.content.jobs.persona_job.generate_personas_for_user",
                new=AsyncMock(return_value=3),
            ) as mock_spawn,
        ):
            from private_internet.content.jobs.persona_job import run_persona_evolution_job
            result = await run_persona_evolution_job(user_id=uid)

        mock_spawn.assert_called_once_with(uid)
        assert result["spawned"] == 3

    @pytest.mark.anyio
    async def test_user_id_required(self):
        with pytest.raises(AssertionError):
            from private_internet.content.jobs.persona_job import run_persona_evolution_job
            await run_persona_evolution_job(user_id=None)


# ── creator_selector: user scoping ───────────────────────────────────────────

class TestCreatorSelectorUserScoping:
    def test_query_includes_user_id_filter(self):
        """The SQL issued by select_for_topic must scope by (user_id = X OR user_id IS NULL)."""
        from private_internet.content.creator_selector import CreatorSelector

        uid = str(uuid.uuid4())
        creator = {
            "id": str(uuid.uuid4()),
            "slug": "test-persona",
            "name": "Test Persona",
            "style_prompt": "Write concisely.",
            "topic_affinities": ["tech"],
            "score": 0.7,
            "is_active": True,
        }
        topic = {"id": str(uuid.uuid4()), "name": "AI trends", "keywords": ["AI", "tech"]}

        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchall.side_effect = [[creator], []]
        conn.cursor.return_value = cursor

        selector = CreatorSelector()
        result = selector.select_for_topic(conn, topic, user_id=uid)

        assert result["slug"] == "test-persona"
        # Verify that user_id was passed to the cursor execute calls
        all_calls = cursor.execute.call_args_list
        # At least one call must include the user_id in its params
        user_id_in_params = any(
            uid in (args[1] if len(args) > 1 and isinstance(args[1], (list, tuple)) else [])
            for args in [call.args for call in all_calls]
        )
        assert user_id_in_params, "user_id must be threaded into at least one DB query param"
