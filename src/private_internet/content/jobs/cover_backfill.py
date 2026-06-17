"""One-off cover / thumbnail backfill for EXISTING content (demo prep).

Scoped to a single user. Reuses the live pipelines' generators via
``cover_art.generate_cover`` / ``PostImageGenerator`` / STORIES ``_generate_poster``
so backfilled covers are real fal.ai imagery when the balance is funded, and the
designed local fallback otherwise. Idempotent and safe to re-run.

Scope = "fill missing + refresh video/film":
  - PULSE posts:   image_url  IS NULL                -> generate + upload
  - ARIA tracks:   art_s3_key IS NULL (status ready) -> generate + upload
  - SIGNAL videos: every video with a video_url      -> REGENERATE thumbnail
  - STORIES films: every ready film                  -> REGENERATE poster/thumbnail

Each item's slow part is the fal.ai render (an awaited HTTP call). Those run
CONCURRENTLY, bounded by ``_CONCURRENCY`` — a fully-sequential run overran the
backfill workflow's poll window. DB reads happen up front and DB writes happen
after the renders complete, both on the single shared connection, so the
connection is never touched from inside the concurrent workers.

Per-item failures are logged and skipped (one bad item never aborts the run).
"""

import asyncio
import logging
from typing import Awaitable, Callable, Optional, TypeVar

from psycopg2.extras import RealDictCursor

from private_internet.database import _connect
from private_internet.content.asset_store import AssetStore
from private_internet.content.cover_art import generate_cover
from private_internet.content.image_generator import PostImageGenerator
from private_internet.content.video_generator import VIDEO_WIDTH, VIDEO_HEIGHT

logger = logging.getLogger(__name__)

# How many fal renders to run at once. The renders are the bottleneck (a few
# seconds each); rendering them serially overran the 12-minute backfill workflow.
# Kept modest so we don't trip fal rate limits or open too many sockets.
_CONCURRENCY = 5

_T = TypeVar("_T")


async def _render_all(
    items: list[_T], render: Callable[[_T], Awaitable[Optional[str]]]
) -> list[tuple[_T, Optional[str], Optional[Exception]]]:
    """Run ``render`` over ``items`` with bounded concurrency.

    ``render`` does only the fal call + S3 upload (no DB) and returns the asset
    URL. Returns one (item, url, error) tuple per item; the caller applies the DB
    writes sequentially afterwards.
    """
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def _guarded(item: _T) -> tuple[_T, Optional[str], Optional[Exception]]:
        async with sem:
            try:
                return item, await render(item), None
            except Exception as exc:  # noqa: BLE001 — one bad item must not abort the run
                return item, None, exc

    return await asyncio.gather(*(_guarded(it) for it in items))


async def _backfill_pulse(conn, store: AssetStore, user_id: str) -> dict:
    """PULSE posts that came out without an image (image_url IS NULL)."""
    image_gen = PostImageGenerator()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """SELECT id, body, creator_id, topic_id
           FROM content_posts
           WHERE user_id = %s AND image_url IS NULL""",
        (user_id,),
    )
    posts = [dict(r) for r in cur.fetchall()]
    cur.close()

    # Resolve each post's creator + topic up front (sequential DB reads), so the
    # concurrent render workers never touch the shared connection.
    renderable: list[dict] = []
    failed = 0
    for post in posts:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM content_creators WHERE id = %s", (post["creator_id"],))
        creator = dict(cur.fetchone() or {})
        cur.execute(
            "SELECT * FROM content_topics WHERE id = %s AND user_id = %s",
            (post["topic_id"], user_id),
        )
        topic = dict(cur.fetchone() or {})
        cur.close()
        if not creator or not topic:
            logger.warning("PULSE post %s — missing creator/topic, skipping", post["id"])
            failed += 1
            continue
        post["_creator"], post["_topic"] = creator, topic
        renderable.append(post)

    async def _render(post: dict) -> str:
        image_bytes, image_prompt = await image_gen.generate_for_post(
            post["_topic"], post["_creator"], post["body"]
        )
        post["_image_prompt"] = image_prompt
        return store.upload_post_image(image_bytes, post["id"])

    done = 0
    for post, url, exc in await _render_all(renderable, _render):
        if exc is not None or url is None:
            failed += 1
            logger.error("PULSE post %s — backfill failed: %s", post["id"], exc, exc_info=exc)
            continue
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE content_posts SET image_url = %s, image_prompt = %s "
                "WHERE id = %s AND user_id = %s",
                (url, post.get("_image_prompt"), post["id"], user_id),
            )
            conn.commit()
            cur.close()
            done += 1
            logger.info("PULSE post %s — cover set (%s)", post["id"], url)
        except Exception as exc:
            conn.rollback()
            failed += 1
            logger.error("PULSE post %s — db update failed: %s", post["id"], exc, exc_info=True)

    return {"module": "pulse", "candidates": len(posts), "done": done, "failed": failed}


async def _backfill_aria(conn, store: AssetStore, user_id: str) -> dict:
    """ARIA tracks missing album art (art_s3_key IS NULL)."""
    from private_internet.content.aria.generator import _upload_aria_art, _s3_key_from_cdn

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """SELECT id, title, mood, genre
           FROM aria_tracks
           WHERE user_id = %s AND art_s3_key IS NULL AND status = 'ready'""",
        (user_id,),
    )
    tracks = [dict(r) for r in cur.fetchall()]
    cur.close()

    async def _render(track: dict) -> str:
        tid = str(track["id"])
        mood = str(track.get("mood") or "")
        genre = track.get("genre") or "ambient"
        art_prompt = f"abstract album art, {mood} mood, {genre}, no text"
        art_bytes = await generate_cover(
            art_prompt, 1024, 1024,
            fallback_title=track.get("title", "Untitled"),
            kicker="ARIA",
            fallback_subtitle=mood.capitalize(),
            seed=tid,
        )
        art_cdn = _upload_aria_art(store, art_bytes, tid)
        return _s3_key_from_cdn(art_cdn, store)

    done, failed = 0, 0
    for track, art_key, exc in await _render_all(tracks, _render):
        if exc is not None or art_key is None:
            failed += 1
            logger.error("ARIA track %s — backfill failed: %s", track["id"], exc, exc_info=exc)
            continue
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE aria_tracks SET art_s3_key = %s, updated_at = now() "
                "WHERE id = %s AND user_id = %s",
                (art_key, track["id"], user_id),
            )
            conn.commit()
            cur.close()
            done += 1
            logger.info("ARIA track %s — art set (%s)", track["id"], art_key)
        except Exception as exc:
            conn.rollback()
            failed += 1
            logger.error("ARIA track %s — db update failed: %s", track["id"], exc, exc_info=True)

    return {"module": "aria", "candidates": len(tracks), "done": done, "failed": failed}


async def _backfill_signal(conn, store: AssetStore, user_id: str) -> dict:
    """Refresh the thumbnail of every SIGNAL video that has a rendered video."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """SELECT v.id, v.title, c.name AS creator_name
           FROM content_videos v
           LEFT JOIN content_creators c ON c.id = v.creator_id
           WHERE v.user_id = %s AND v.video_url IS NOT NULL""",
        (user_id,),
    )
    videos = [dict(r) for r in cur.fetchall()]
    cur.close()

    async def _render(video: dict) -> str:
        title = video.get("title") or ""
        prompt = (
            f"{title}. cinematic, 16:9, dark editorial style, "
            "high contrast, dramatic lighting, no text"
        )
        thumb = await generate_cover(
            prompt, VIDEO_WIDTH, VIDEO_HEIGHT,
            fallback_title=title,
            kicker="SIGNAL",
            fallback_subtitle=video.get("creator_name") or "",
            seed=str(video["id"]),
        )
        return store.upload_thumbnail(thumb, video["id"])

    done, failed = 0, 0
    for video, url, exc in await _render_all(videos, _render):
        if exc is not None or url is None:
            failed += 1
            logger.error("SIGNAL video %s — backfill failed: %s", video["id"], exc, exc_info=exc)
            continue
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE content_videos SET thumbnail_url = %s WHERE id = %s AND user_id = %s",
                (url, video["id"], user_id),
            )
            conn.commit()
            cur.close()
            done += 1
            logger.info("SIGNAL video %s — thumbnail refreshed (%s)", video["id"], url)
        except Exception as exc:
            conn.rollback()
            failed += 1
            logger.error("SIGNAL video %s — db update failed: %s", video["id"], exc, exc_info=True)

    return {"module": "signal", "candidates": len(videos), "done": done, "failed": failed}


async def _backfill_stories(conn, store: AssetStore, user_id: str) -> dict:
    """Refresh poster + thumbnail of every ready STORIES film."""
    from private_internet.content.stories.generator import _generate_poster

    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """SELECT id, title, premise
           FROM stories_films
           WHERE user_id = %s AND status = 'ready'""",
        (user_id,),
    )
    films = [dict(r) for r in cur.fetchall()]
    cur.close()

    async def _render(film: dict) -> str:
        fid = str(film["id"])
        poster = await _generate_poster(film.get("title", ""), film.get("premise"))
        return store._upload(f"stories/{fid}/poster.png", poster, "image/png")

    done, failed = 0, 0
    for film, url, exc in await _render_all(films, _render):
        if exc is not None or url is None:
            failed += 1
            logger.error("STORIES film %s — backfill failed: %s", film["id"], exc, exc_info=exc)
            continue
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE stories_films SET thumbnail_url = %s, poster_url = %s, updated_at = now() "
                "WHERE id = %s AND user_id = %s",
                (url, url, film["id"], user_id),
            )
            conn.commit()
            cur.close()
            done += 1
            logger.info("STORIES film %s — poster refreshed (%s)", film["id"], url)
        except Exception as exc:
            conn.rollback()
            failed += 1
            logger.error("STORIES film %s — db update failed: %s", film["id"], exc, exc_info=True)

    return {"module": "stories", "candidates": len(films), "done": done, "failed": failed}


async def backfill_covers(user_id: str) -> dict:
    """Backfill covers for one user across all content modules. # MUST SCOPE BY USER."""
    assert user_id, "user_id is required"
    store = AssetStore()
    conn = _connect()
    results = []
    try:
        results.append(await _backfill_pulse(conn, store, user_id))
        results.append(await _backfill_aria(conn, store, user_id))
        results.append(await _backfill_signal(conn, store, user_id))
        results.append(await _backfill_stories(conn, store, user_id))
    finally:
        conn.close()

    summary = {r["module"]: {k: r[k] for k in ("candidates", "done", "failed")} for r in results}
    logger.info("cover backfill complete for user %s: %s", user_id[:8], summary)
    return summary
