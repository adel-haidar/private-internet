"""Per-user AI-generated creator personas for the PULSE pipeline.

Called during user provisioning (best-effort) and via the persona evolution job.
Each generated persona is inserted into `content_creators` with the caller's
`user_id`, making it private to that user.

Brain-driven: reads the user's dominant topics + language and asks Bedrock to
invent 3-5 fictional personas that feel natural for someone with those interests,
writing in the user's own language.

Fallback: if the user's brain is empty/sparse, creates a small set of
"international basics" (sport, weather, interesting facts) still in the user's
language — harmless universals with no country/region bias.

All operations are idempotent: existing slugs for the same user_id are skipped.
# MUST SCOPE BY USER
"""

import json
import logging
import uuid
from typing import Optional

from psycopg2.extras import RealDictCursor

from private_internet.content.llm import converse_text
from private_internet.content.user_language import resolve_user_language
from private_internet.content.voice_config import language_name
from private_internet.database import _connect

logger = logging.getLogger(__name__)

# Temperature for creative persona generation (documented here per policy).
_PERSONA_TEMPERATURE = 0.8

# Fallback set used when the brain is empty — universals with no cultural bias.
_FALLBACK_PERSONA_TEMPLATES = [
    {
        "name_template": "The Sports Correspondent",
        "bio_template": "Covers the human side of athletic performance around the world.",
        "style_hint": "Warm, precise, avoids clichés. Leads with the person, not the score.",
        "affinities": ["sport", "fitness", "athletics", "performance", "health"],
        "slug_suffix": "sports-correspondent",
    },
    {
        "name_template": "The Curious Observer",
        "bio_template": "Finds the unexpected angle on everyday phenomena worldwide.",
        "style_hint": "Conversational, delighted by surprise. Opens with the surprising fact.",
        "affinities": ["culture", "ideas", "science", "history", "psychology"],
        "slug_suffix": "curious-observer",
    },
    {
        "name_template": "The Tech Realist",
        "bio_template": "Cuts through hype to explain what technology actually changes.",
        "style_hint": "Sceptical but fair. Dense with insight, sparse with words.",
        "affinities": ["technology", "AI", "software", "innovation", "future"],
        "slug_suffix": "tech-realist",
    },
]


def _fetch_user_top_topics(user_id: str, limit: int = 10) -> list[dict]:
    """Return the user's highest-weight topics for persona generation context.
    # MUST SCOPE BY USER
    """
    conn = _connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """SELECT name, keywords, weight FROM content_topics
               WHERE user_id = %s
               ORDER BY weight DESC
               LIMIT %s""",
            (user_id, limit),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()
        conn.close()


def _existing_user_slugs(user_id: str) -> set[str]:
    """Return slug set of personas already generated for this user.
    # MUST SCOPE BY USER
    """
    conn = _connect()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT slug FROM content_creators WHERE user_id = %s",
            (user_id,),
        )
        return {r[0] for r in cur.fetchall()}
    finally:
        cur.close()
        conn.close()


def _insert_persona(user_id: str, persona: dict) -> None:
    """Insert one persona row.  # MUST SCOPE BY USER"""
    conn = _connect()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO content_creators
               (id, slug, name, bio, style_prompt,
                polly_voice_id, polly_language_code, topic_affinities,
                user_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT (slug) DO NOTHING""",
            (
                str(uuid.uuid4()),
                persona["slug"],
                persona["name"],
                persona["bio"],
                persona["style_prompt"],
                persona.get("polly_voice_id", "Joanna"),
                persona.get("polly_language_code", "en-US"),
                persona.get("topic_affinities", []),
                user_id,
            ),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


async def _generate_personas_via_bedrock(
    topics: list[dict],
    language_code: str,
    user_id: str,
) -> list[dict]:
    """Call Bedrock to generate 3-5 persona dicts from the user's topic context.

    Returns a list of persona dicts. Empty list on any error.
    """
    lang_name = language_name(language_code)
    topic_summary = "\n".join(
        f"- {t['name']} (keywords: {', '.join((t.get('keywords') or [])[:5])})"
        for t in topics[:8]
    )

    system_prompt = (
        "You are a persona design expert. Given a person's interests, you design "
        "fictional social-media creator personas who would naturally post about those topics. "
        "Each persona must be believable, distinct in voice, and appropriate for someone "
        "who thinks in the given language. "
        "Output ONLY a JSON array of 3 to 5 persona objects with these exact keys:\n"
        '  "slug" (lowercase-hyphenated, globally unique — include a random 4-char suffix),\n'
        '  "name" (persona display name),\n'
        '  "bio" (1-2 sentence bio),\n'
        '  "style_prompt" (writing style instruction for the LLM, 2-4 sentences),\n'
        '  "polly_voice_id" (AWS Polly voice id appropriate for the language, e.g. "Takumi" for ja),\n'
        '  "polly_language_code" (BCP-47 code, e.g. "ja-JP"),\n'
        '  "topic_affinities" (list of 4-8 topic keywords in the persona\'s language),\n'
        '  "valid_tones" (subset of ["informative","satirical","supportive","critical"]).\n'
        "No preamble, no explanation, no markdown fences."
    )
    user_prompt = (
        f"User language: {lang_name} ({language_code})\n\n"
        f"User's top topics:\n{topic_summary}\n\n"
        f"Design 3-5 fictional creator personas who would post naturally about these topics "
        f"and write entirely in {lang_name}. "
        f"Make each persona feel like a real, distinct human voice — not a generic AI. "
        f"Slug must include a short random alphanumeric suffix to avoid collisions."
    )

    try:
        text, _usage = await converse_text(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=_PERSONA_TEMPERATURE,
            max_tokens=2048,
        )
        # Strip markdown fences if present
        t = text.strip()
        if t.startswith("```"):
            t = t[7:] if t.startswith("```json") else t[3:]
            if t.endswith("```"):
                t = t[:-3]
            t = t.strip()
        personas = json.loads(t)
        if not isinstance(personas, list):
            raise ValueError("expected JSON array")
        return personas
    except Exception as e:
        logger.warning(
            "[user:%s] persona Bedrock generation failed: %s",
            user_id[:8],
            e,
        )
        return []


def _build_fallback_personas(language_code: str, user_id: str) -> list[dict]:
    """Build a small set of language-localised fallback personas when the brain
    is sparse. Slugs are suffixed with user_id[:6] for isolation."""
    lang_name = language_name(language_code)
    result = []
    for tmpl in _FALLBACK_PERSONA_TEMPLATES:
        slug = f"{tmpl['slug_suffix']}-{user_id[:6]}"
        result.append({
            "slug": slug,
            "name": tmpl["name_template"],
            "bio": tmpl["bio_template"],
            "style_prompt": (
                f"{tmpl['style_hint']} "
                f"Write the entire post in {lang_name}. "
                f"Not English unless {lang_name} is English."
            ),
            "polly_voice_id": "Joanna",
            "polly_language_code": f"{language_code}-{'JP' if language_code == 'ja' else 'US'}",
            "topic_affinities": tmpl["affinities"],
            "valid_tones": ["informative", "supportive"],
        })
    return result


async def generate_personas_for_user(user_id: str) -> int:
    """Generate and persist 3-5 brain-driven personas for one user.

    Idempotent: already-inserted slugs are skipped. Returns count inserted.
    # MUST SCOPE BY USER
    """
    assert user_id is not None, "user_id must be set before any content operation"

    language_code = resolve_user_language(user_id)
    topics = _fetch_user_top_topics(user_id)
    existing_slugs = _existing_user_slugs(user_id)

    if topics:
        raw_personas = await _generate_personas_via_bedrock(topics, language_code, user_id)
    else:
        raw_personas = []
        logger.info("[user:%s] brain is sparse — using fallback personas", user_id[:8])

    if not raw_personas:
        raw_personas = _build_fallback_personas(language_code, user_id)

    inserted = 0
    for p in raw_personas:
        slug = p.get("slug", "")
        if not slug:
            continue
        if slug in existing_slugs:
            logger.debug("[user:%s] persona slug '%s' already exists — skipping", user_id[:8], slug)
            continue
        try:
            _insert_persona(user_id, p)
            existing_slugs.add(slug)
            inserted += 1
            logger.info("[user:%s] persona '%s' (%s) inserted", user_id[:8], p.get("name"), slug)
        except Exception as e:
            logger.warning("[user:%s] failed to insert persona '%s': %s", user_id[:8], slug, e)

    logger.info("[user:%s] generate_personas_for_user: %d new personas", user_id[:8], inserted)
    return inserted
