"""PULSE post generation batch job (Phase 3, Task 5)."""

import uuid
import logging
from datetime import datetime, timedelta, timezone

from psycopg2.extras import RealDictCursor

from private_internet.billing.plans import feature_enabled_for_user
from private_internet.database import _connect
from private_internet.content.creator_selector import CreatorSelector
from private_internet.content.post_generator import PostTextGenerator
from private_internet.content.image_generator import PostImageGenerator
from private_internet.content.asset_store import AssetStore
from private_internet.content.user_language import resolve_user_language

logger = logging.getLogger(__name__)

# Maximum age of a cached post image before we regenerate it.  7 days keeps
# images fresh without re-paying the fal.ai fee on every daily run.
_IMAGE_CACHE_TTL_DAYS = 7


def _lookup_cached_image(conn, topic_id: str, creator_id: str, user_id: str) -> str | None:
    """Return a recently-generated image URL for the same (topic, creator, user)
    if one exists within _IMAGE_CACHE_TTL_DAYS, else None.

    Cache key: (topic_id, creator_id, user_id) — scoped so cross-user images
    are never shared even if they happen to share a topic.
    # MUST SCOPE BY USER
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=_IMAGE_CACHE_TTL_DAYS)
    cur = conn.cursor()
    try:
        cur.execute(
            """SELECT image_url FROM content_posts
               WHERE user_id = %s
                 AND topic_id = %s
                 AND creator_id = %s
                 AND image_url IS NOT NULL
                 AND created_at >= %s
               ORDER BY created_at DESC
               LIMIT 1""",
            (user_id, topic_id, creator_id, cutoff),
        )
        row = cur.fetchone()
        return row[0] if row else None
    except Exception as e:
        logger.warning(f"Image cache lookup failed (will regenerate): {e}")
        return None
    finally:
        cur.close()


async def generate_posts_batch(count: int = 3, *, user_id: str) -> dict:
    """
    Generate posts for a single user from that user's own topics.
    # MUST SCOPE BY USER

    1. Query content_topics ordered by weight DESC, last_used_at ASC NULLS FIRST
       (prefer untouched high-weight topics)
    2. For each topic: select creator + tone, generate text + image,
       upload image to S3, insert into content_posts, bump topic usage.
    3. Log: N posts created, total Bedrock tokens used.

    Image failure is non-fatal: the post is still created with image_url=NULL.
    """
    assert user_id is not None, "user_id must be set before any content operation"
    logger.info(f"[user:{user_id[:8]}] Starting generate_posts_batch (count={count})")

    # Resolve once and pass down — avoids repeated DB lookups per topic.
    language_code = resolve_user_language(user_id)
    logger.info(f"[user:{user_id[:8]}] resolved language: {language_code}")

    # PULSE images are a Pro+ feature ("pulse_media"). Free users still get a
    # full text feed — just no AI-generated post images.
    media_enabled = feature_enabled_for_user(user_id, "pulse_media")

    selector = CreatorSelector()
    text_generator = PostTextGenerator()
    image_generator = PostImageGenerator()
    asset_store = AssetStore()

    conn = _connect()
    created = 0
    failed = 0
    total_input_tokens = 0
    total_output_tokens = 0

    try:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """SELECT * FROM content_topics
               WHERE user_id = %s
               -- Prefer the user's real (memory-derived) topics over the generic
               -- onboarding seed topics, so the feed reflects their actual brain.
               ORDER BY (source = 'bootstrap') ASC, weight DESC, last_used_at ASC NULLS FIRST
               LIMIT %s""",
            (user_id, count),
        )
        topics = [dict(r) for r in cur.fetchall()]
        cur.close()

        if not topics:
            logger.info("No topics available — run the topic intelligence job first.")
            return {"created": 0, "failed": 0}

        for topic in topics:
            try:
                # a/b. Pick creator + tone (scoped to this user's visible personas)
                creator = selector.select_for_topic(conn, topic, user_id=user_id)
                tone = selector.select_tone(creator, topic)

                # Fetch research for the prompt
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute(
                    """SELECT * FROM content_research
                       WHERE user_id = %s AND topic_id = %s
                       ORDER BY fetched_at DESC LIMIT 5""",
                    (user_id, topic["id"]),
                )
                research = [dict(r) for r in cur.fetchall()]
                cur.close()

                # c. Generate post text in the user's language.
                # Returns None if the post failed validation twice — skip.
                post = await text_generator.generate(
                    topic, creator, tone, research, language_code=language_code
                )
                if post is None:
                    failed += 1
                    logger.warning(
                        f"Skipping topic '{topic['name']}' — post generation "
                        "failed validation."
                    )
                    continue
                total_input_tokens += post.usage.get("inputTokens", 0)
                total_output_tokens += post.usage.get("outputTokens", 0)

                post_id = str(uuid.uuid4())

                # d/e. Generate + upload image (Pro+; non-fatal on failure).
                # Free users get a text-only post (image_url stays NULL).
                #
                # Cache: if this (topic, creator, user) combination already produced
                # an image within _IMAGE_CACHE_TTL_DAYS we reuse the existing CDN URL
                # instead of paying for a new fal.ai generation.  On a cache miss we
                # generate, upload, and persist as usual.
                image_url = None
                image_prompt = None
                if media_enabled:
                    cached_url = _lookup_cached_image(
                        conn, topic["id"], creator["id"], user_id
                    )
                    if cached_url:
                        image_url = cached_url
                        logger.info(
                            f"Image cache HIT for topic='{topic['name']}' "
                            f"creator='{creator['slug']}' — reusing {cached_url}"
                        )
                    else:
                        try:
                            image_bytes, image_prompt = await image_generator.generate_for_post(
                                topic, creator, post.body
                            )
                            image_url = asset_store.upload_post_image(image_bytes, post_id)
                        except Exception as e:
                            logger.warning(
                                f"Image generation failed for topic '{topic['name']}' — "
                                f"creating post without image: {e}"
                            )

                # f. Insert the post
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO content_posts
                       (id, creator_id, topic_id, body, image_url, image_prompt, tone,
                        post_format, user_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (post_id, creator["id"], topic["id"], post.body, image_url, image_prompt,
                     tone, post.post_format, user_id),
                )

                # g. Bump topic usage
                cur.execute(
                    """UPDATE content_topics
                       SET used_count = used_count + 1, last_used_at = %s
                       WHERE id = %s AND user_id = %s""",
                    (datetime.now(timezone.utc), topic["id"], user_id),
                )
                conn.commit()
                cur.close()

                created += 1
                logger.info(
                    f"Created post {post_id} — creator='{creator['slug']}', "
                    f"tone={tone}, topic='{topic['name']}', image={'yes' if image_url else 'no'}"
                )
            except Exception as e:
                conn.rollback()
                failed += 1
                logger.error(f"Failed to create post for topic '{topic.get('name')}': {e}", exc_info=True)
    finally:
        conn.close()

    logger.info(
        f"generate_posts_batch completed. Created: {created}, Failed: {failed}, "
        f"Bedrock tokens: {total_input_tokens} in / {total_output_tokens} out"
    )
    return {
        "created": created,
        "failed": failed,
        "input_tokens": total_input_tokens,
        "output_tokens": total_output_tokens,
    }
