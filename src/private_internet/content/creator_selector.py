"""Creator persona selection for the PULSE post pipeline (Phase 3, Task 1)."""

import random
import logging
from datetime import datetime, timezone

from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

ALL_TONES = ["informative", "satirical", "supportive", "critical"]

# Valid tones per creator persona (by slug). Unknown creators get all tones.
_TONE_MAP = {
    "maksim-volkov": ["satirical", "critical"],
    "dr-layla-nasser": ["informative", "critical"],
    "felix-bergmann": ["satirical", "supportive"],
    "nora-chen": ["supportive", "informative"],
    "viktor-ostrowski": ["satirical"],
}

# How much each affinity keyword hit contributes to the selection score.
_AFFINITY_WEIGHT = 0.4
# Penalty if the creator already posted about this topic in the last 7 days.
_RECENCY_PENALTY = 0.5


class CreatorSelector:
    def select_for_topic(self, db, topic: dict) -> dict:
        """
        Pick the best creator (row dict) for a topic (row dict from content_topics).

        1. Filter active creators (is_active=True, score >= 0.3)
        2. Score each by affinity match + RL score - recency penalty
        3. Multiply by random.uniform(0.85, 1.0) for editorial variety
        4. Fallback: if no creator scores > 0.1, return highest overall score creator
        """
        cur = db.cursor(cursor_factory=RealDictCursor)
        try:
            cur.execute(
                "SELECT * FROM content_creators WHERE is_active = TRUE AND score >= 0.3"
            )
            creators = [dict(r) for r in cur.fetchall()]
            if not creators:
                # All creators retired/low-score — fall back to the best one overall
                cur.execute(
                    "SELECT * FROM content_creators WHERE is_active = TRUE "
                    "ORDER BY score DESC LIMIT 1"
                )
                row = cur.fetchone()
                if row is None:
                    raise RuntimeError("No active creators available")
                return dict(row)

            # Creators that posted about this topic in the last 7 days
            cur.execute(
                """SELECT DISTINCT creator_id FROM content_posts
                   WHERE topic_id = %s AND created_at >= now() - INTERVAL '7 days'""",
                (topic["id"],),
            )
            recent_creator_ids = {r["creator_id"] for r in cur.fetchall()}
        finally:
            cur.close()

        topic_terms = self._topic_terms(topic)

        best_creator = None
        best_score = float("-inf")
        for creator in creators:
            affinity_hits = self._affinity_match(topic_terms, creator.get("topic_affinities") or [])
            score = affinity_hits * _AFFINITY_WEIGHT + float(creator.get("score") or 0.0)
            if creator["id"] in recent_creator_ids:
                score -= _RECENCY_PENALTY
            score *= random.uniform(0.85, 1.0)
            if score > best_score:
                best_score = score
                best_creator = creator

        if best_score <= 0.1:
            # Nothing matched meaningfully — fall back to highest RL score
            best_creator = max(creators, key=lambda c: float(c.get("score") or 0.0))
            logger.info(
                f"No creator scored > 0.1 for topic '{topic.get('name')}'; "
                f"falling back to '{best_creator['slug']}'"
            )

        return best_creator

    def select_tone(self, creator: dict, topic: dict) -> str:
        """
        Pick a tone from the creator's valid tones, with a 20% chance of
        flipping to a different tone for variety.
        """
        valid = _TONE_MAP.get(creator.get("slug"), ALL_TONES)
        tone = random.choice(valid)
        if random.random() < 0.2:
            others = [t for t in ALL_TONES if t != tone]
            tone = random.choice(others)
        return tone

    @staticmethod
    def _topic_terms(topic: dict) -> list[str]:
        """Lowercased keywords + name tokens for affinity matching."""
        terms = [k.lower() for k in (topic.get("keywords") or [])]
        terms += [w.lower() for w in (topic.get("name") or "").split() if len(w) > 3]
        return terms

    @staticmethod
    def _affinity_match(topic_terms: list[str], affinities: list[str]) -> int:
        """Count creator affinities that appear in (or contain) any topic term."""
        hits = 0
        for affinity in affinities:
            a = affinity.lower()
            if any(a in term or term in a for term in topic_terms):
                hits += 1
        return hits
