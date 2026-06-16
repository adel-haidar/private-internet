"""Resolve the BCP-47 language a user predominantly *thinks in*, for content gen.

Shared by the PULSE and SIGNAL pipelines so generated posts, topic names, video
scripts, and TTS voices come out in the user's own language instead of always
English. Reuses the same deterministic resolver ARIA uses for podcasts
(`language_resolver.resolve_dominant_language`); the only new piece is loading a
user's memories with their detected `language` column and picking a fallback.

# MUST SCOPE BY USER — every query here is filtered by user_id.
"""

import logging

from psycopg2.extras import RealDictCursor

from private_internet.database import _connect
from private_internet.content.language_resolver import resolve_dominant_language

logger = logging.getLogger(__name__)

# Hard floor when a user has no language signal at all (empty/brand-new brain).
_DEFAULT_LANGUAGE = "en"


def _fetch_user_memory_languages(user_id: str) -> tuple[list[dict], str]:
    """Return (memories, fallback_language) for one user.

    memories: list of {id, content, language} for every active memory.
    fallback_language: the language of the onboarding/introduction memory if one
    has a detected language, else the platform default ("en"). Used by
    resolve_dominant_language on a tie or when there is no dominant language.
    # MUST SCOPE BY USER
    """
    conn = _connect()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """SELECT memory_id, content, language, tags
               FROM memories
               WHERE user_id = %s AND merged_into IS NULL
               ORDER BY created_at ASC""",
            (user_id,),
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    memories = [
        {"id": r["memory_id"], "content": r["content"] or "", "language": r["language"]}
        for r in rows
    ]

    # Fallback: the introduction/onboarding memory's language, if detected.
    fallback = _DEFAULT_LANGUAGE
    for r in rows:
        tags = (r["tags"] or "").lower()
        if r["language"] and ("introduction" in tags or "onboarding" in tags):
            fallback = r["language"]
            break

    return memories, fallback


def resolve_user_language(user_id: str) -> str:
    """Return the BCP-47 code (e.g. 'ja', 'en') the user predominantly thinks in.

    Deterministic, no LLM. Falls back to the onboarding memory's language, then
    to "en", on a tie or when the brain has no language signal.
    # MUST SCOPE BY USER
    """
    assert user_id is not None, "user_id must be set before any content operation"
    try:
        memories, fallback = _fetch_user_memory_languages(user_id)
        return resolve_dominant_language(memories, fallback)
    except Exception as e:
        logger.warning(
            f"[user:{user_id[:8]}] language resolution failed, defaulting to "
            f"'{_DEFAULT_LANGUAGE}': {e}",
            exc_info=True,
        )
        return _DEFAULT_LANGUAGE
