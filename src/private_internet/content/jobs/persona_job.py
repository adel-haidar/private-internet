"""Persona evolution job for the PULSE pipeline.

Scheduled via `core/jobs.run_for_all_users`. For each user it:
  1. Reads engagement from `content_interactions` per creator (for this user's posts).
  2. Retires stale personas: active user-owned personas with 0 interactions in
     the last 30 days after at least 5 posts — marked is_active=FALSE.
  3. Spawns new personas reflecting the user's emerging topics (topics that grew
     in weight since the last persona generation pass).

Conservative and idempotent:
  - Global (user_id=NULL) personas are NEVER touched.
  - Retirement requires both low engagement AND a meaningful post count (>= 5)
    to avoid retiring new personas that simply haven't been shown much yet.
  - New personas are only generated when there are 3+ new/evolved topics that
    lack a persona with matching affinities.
  - A user's total active personal personas is capped at 10 to bound cost.

# MUST SCOPE BY USER
"""

import logging

from psycopg2.extras import RealDictCursor

from private_internet.content.persona_generator import generate_personas_for_user
from private_internet.database import _connect

logger = logging.getLogger(__name__)

# Retire personas with fewer than this many interactions per post after this
# many posts — avoids premature retirement of freshly-created personas.
_MIN_POSTS_BEFORE_RETIREMENT = 5
_RETIREMENT_INTERACTION_RATE = 0.05  # < 5% interaction rate triggers retirement
_RETIREMENT_DAYS = 30
_MAX_ACTIVE_USER_PERSONAS = 10
# Only spawn new personas when this many "uncovered" topics exist
_SPAWN_TOPIC_THRESHOLD = 3


def _get_user_persona_engagement(conn, user_id: str) -> list[dict]:
    """Return per-creator engagement stats for this user's posts.

    Returns dicts: {creator_id, slug, post_count, interaction_count,
                    interaction_rate, is_active}
    # MUST SCOPE BY USER
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """
            SELECT
                cc.id             AS creator_id,
                cc.slug,
                cc.is_active,
                COUNT(DISTINCT cp.id)          AS post_count,
                COUNT(DISTINCT ci.id)          AS interaction_count
            FROM content_creators cc
            LEFT JOIN content_posts cp
                ON cp.creator_id = cc.id
                AND cp.user_id = %s
                AND cp.created_at >= now() - INTERVAL '%s days'
            LEFT JOIN content_interactions ci
                ON ci.content_id = cp.id
                AND ci.content_type = 'post'
            WHERE cc.user_id = %s
              AND cc.is_active = TRUE
            GROUP BY cc.id, cc.slug, cc.is_active
            """,
            (user_id, _RETIREMENT_DAYS, user_id),
        )
        rows = [dict(r) for r in cur.fetchall()]
    finally:
        cur.close()

    for r in rows:
        pc = r["post_count"] or 0
        ic = r["interaction_count"] or 0
        r["post_count"] = pc
        r["interaction_count"] = ic
        r["interaction_rate"] = ic / pc if pc > 0 else 0.0
    return rows


def _retire_persona(conn, creator_id: str, user_id: str, slug: str) -> None:
    """Mark a user-owned persona as inactive.  # MUST SCOPE BY USER"""
    cur = conn.cursor()
    try:
        cur.execute(
            """UPDATE content_creators
               SET is_active = FALSE
               WHERE id = %s AND user_id = %s""",
            (creator_id, user_id),
        )
        conn.commit()
        logger.info("[user:%s] retired stale persona '%s'", user_id[:8], slug)
    finally:
        cur.close()


def _count_active_user_personas(conn, user_id: str) -> int:
    """# MUST SCOPE BY USER"""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT COUNT(*) FROM content_creators WHERE user_id = %s AND is_active = TRUE",
            (user_id,),
        )
        return cur.fetchone()[0]
    finally:
        cur.close()


def _uncovered_topic_count(conn, user_id: str) -> int:
    """Return how many of the user's top topics lack a persona with a matching
    affinity. Topics with no affinity match = no specialised persona to post.
    # MUST SCOPE BY USER
    """
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(
            """SELECT name, keywords FROM content_topics
               WHERE user_id = %s
               ORDER BY weight DESC LIMIT 15""",
            (user_id,),
        )
        topics = [dict(r) for r in cur.fetchall()]

        cur.execute(
            """SELECT topic_affinities FROM content_creators
               WHERE user_id = %s AND is_active = TRUE""",
            (user_id,),
        )
        all_affinities: set[str] = set()
        for row in cur.fetchall():
            for aff in (row["topic_affinities"] or []):
                all_affinities.add(aff.lower())
    finally:
        cur.close()

    uncovered = 0
    for topic in topics:
        kws = [k.lower() for k in (topic.get("keywords") or [])]
        name_terms = [w.lower() for w in (topic.get("name") or "").split()]
        all_terms = set(kws + name_terms)
        if not any(aff in all_terms or any(t in aff for t in all_terms) for aff in all_affinities):
            uncovered += 1
    return uncovered


async def run_persona_evolution_job(*, user_id: str) -> dict:
    """Evolve personas for one user. Fanned out via run_for_all_users.
    # MUST SCOPE BY USER
    """
    assert user_id is not None, "user_id must be set before any content operation"
    logger.info("[user:%s] Starting run_persona_evolution_job", user_id[:8])

    conn = _connect()
    try:
        # 1. Collect engagement data for this user's own personas
        engagement = _get_user_persona_engagement(conn, user_id)

        retired = 0
        for entry in engagement:
            if (
                entry["post_count"] >= _MIN_POSTS_BEFORE_RETIREMENT
                and entry["interaction_rate"] < _RETIREMENT_INTERACTION_RATE
            ):
                _retire_persona(conn, entry["creator_id"], user_id, entry["slug"])
                retired += 1

        # 2. Consider spawning new personas
        active_count = _count_active_user_personas(conn, user_id)
        spawned = 0
        if active_count < _MAX_ACTIVE_USER_PERSONAS:
            uncovered = _uncovered_topic_count(conn, user_id)
            if uncovered >= _SPAWN_TOPIC_THRESHOLD:
                logger.info(
                    "[user:%s] %d uncovered topics, %d active personas — spawning new",
                    user_id[:8], uncovered, active_count,
                )
                spawned = await generate_personas_for_user(user_id)
            else:
                logger.info(
                    "[user:%s] %d uncovered topics (< %d threshold) — skipping spawn",
                    user_id[:8], uncovered, _SPAWN_TOPIC_THRESHOLD,
                )
        else:
            logger.info(
                "[user:%s] %d active personas >= cap %d — skipping spawn",
                user_id[:8], active_count, _MAX_ACTIVE_USER_PERSONAS,
            )

    finally:
        conn.close()

    logger.info(
        "[user:%s] persona_evolution_job complete: retired=%d, spawned=%d",
        user_id[:8], retired, spawned,
    )
    return {"retired": retired, "spawned": spawned}
