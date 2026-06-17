"""Snapshot builders — turn a user-owned content item into a public payload.

Every builder is scoped by ``user_id`` (# MUST SCOPE BY USER): a caller can only
share an item they own, and only the fields chosen here are ever made public.

The returned ``snapshot`` dict is stored verbatim on the share row and is the
sole input to the public render path (sharing/page.py). Shape::

    {
      "kind":        str,                  # echoes the share kind
      "kicker":      str,                  # PULSE | SIGNAL | STORIES | ARIA | HEALTH | FINANCE
      "title":       str,                  # og:title
      "subtitle":    str | None,           # small label (creator / mood / hosts)
      "description": str | None,           # og:description
      "body":        str | None,           # long text rendered in the page (post body)
      "media_type":  "image"|"video"|"audio"|"card"|"text",
      "media_url":   str | None,           # the playable asset (video/audio)
      "image_url":   str | None,           # poster / thumbnail / card image (og:image)
    }
"""

from typing import Optional

from fastapi import HTTPException

from private_internet.content.asset_store import AssetStore
from private_internet.core.request_context import RequestContext
from private_internet.database import _connect

# Media-backed kinds resolve an existing item; card kinds render a fresh image.
MEDIA_KINDS = {
    "pulse_post",
    "signal_video",
    "stories_film",
    "stories_episode",
    "aria_track",
    "aria_podcast",
}
CARD_KINDS = {"health_card", "finance_card"}
VALID_KINDS = MEDIA_KINDS | CARD_KINDS


def _truncate(text: Optional[str], limit: int = 200) -> Optional[str]:
    if not text:
        return None
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _key_to_url(key: Optional[str]) -> Optional[str]:
    """S3 key → CloudFront URL, reusing the shared AssetStore cdn_base."""
    if not key:
        return None
    return f"{AssetStore().cdn_base.rstrip('/')}/{key.lstrip('/')}"


def _fetch_one(sql: str, params: tuple) -> Optional[dict]:
    import psycopg2.extras

    conn = _connect()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def build_snapshot(
    ctx: RequestContext,
    kind: str,
    ref_id: Optional[str],
    highlight: Optional[dict],
    token: str,
) -> dict:
    """Build the public snapshot for a share, scoped to the caller.

    Raises HTTPException(400) on a bad request and HTTPException(404) when the
    referenced item does not exist or is not owned by the caller.
    """
    if kind not in VALID_KINDS:
        raise HTTPException(status_code=400, detail=f"unknown share kind: {kind}")

    if kind in CARD_KINDS:
        return _build_card(kind, highlight, token)

    if not ref_id:
        raise HTTPException(status_code=400, detail="ref_id is required for this kind")

    builder = {
        "pulse_post": _build_pulse_post,
        "signal_video": _build_signal_video,
        "stories_film": _build_stories_film,
        "stories_episode": _build_stories_episode,
        "aria_track": _build_aria_track,
        "aria_podcast": _build_aria_podcast,
    }[kind]
    return builder(ctx.user_id, ref_id)


# ── Media-backed builders ────────────────────────────────────────────────────

def _build_pulse_post(user_id: str, ref_id: str) -> dict:
    row = _fetch_one(
        """SELECT p.body, p.image_url, c.name AS creator_name
             FROM content_posts p JOIN content_creators c ON c.id = p.creator_id
            WHERE p.id = %s AND p.user_id = %s""",
        (ref_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="post not found")
    creator = row.get("creator_name") or "Pulse"
    return {
        "kind": "pulse_post",
        "kicker": "PULSE",
        "title": f"{creator} on Pulse",
        "subtitle": creator,
        "description": _truncate(row.get("body")),
        "body": row.get("body"),
        "media_type": "image" if row.get("image_url") else "text",
        "media_url": None,
        "image_url": row.get("image_url"),
    }


def _build_signal_video(user_id: str, ref_id: str) -> dict:
    row = _fetch_one(
        """SELECT v.title, v.description, v.video_url, v.thumbnail_url,
                  c.name AS creator_name
             FROM content_videos v JOIN content_creators c ON c.id = v.creator_id
            WHERE v.id = %s AND v.user_id = %s""",
        (ref_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="video not found")
    return {
        "kind": "signal_video",
        "kicker": "SIGNAL",
        "title": row.get("title") or "A Signal video",
        "subtitle": row.get("creator_name"),
        "description": _truncate(row.get("description")),
        "body": None,
        "media_type": "video",
        "media_url": row.get("video_url"),
        "image_url": row.get("thumbnail_url"),
    }


def _build_stories_film(user_id: str, ref_id: str) -> dict:
    row = _fetch_one(
        """SELECT title, premise, video_url, thumbnail_url, poster_url
             FROM stories_films WHERE id = %s AND user_id = %s""",
        (ref_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="film not found")
    return {
        "kind": "stories_film",
        "kicker": "STORIES",
        "title": row.get("title") or "A Stories film",
        "subtitle": "Film",
        "description": _truncate(row.get("premise")),
        "body": None,
        "media_type": "video",
        "media_url": row.get("video_url"),
        "image_url": row.get("poster_url") or row.get("thumbnail_url"),
    }


def _build_stories_episode(user_id: str, ref_id: str) -> dict:
    row = _fetch_one(
        """SELECT e.title, e.premise, e.video_url, e.thumbnail_url,
                  e.season_number, e.episode_number, s.title AS series_title
             FROM stories_episodes e JOIN stories_series s ON s.id = e.series_id
            WHERE e.id = %s AND e.user_id = %s""",
        (ref_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="episode not found")
    series = row.get("series_title") or "Series"
    label = f"S{row.get('season_number', 1)}E{row.get('episode_number', 1)}"
    return {
        "kind": "stories_episode",
        "kicker": "STORIES",
        "title": f"{series} — {label}: {row.get('title') or ''}".strip(" —:"),
        "subtitle": series,
        "description": _truncate(row.get("premise")),
        "body": None,
        "media_type": "video",
        "media_url": row.get("video_url"),
        "image_url": row.get("thumbnail_url"),
    }


def _build_aria_track(user_id: str, ref_id: str) -> dict:
    row = _fetch_one(
        """SELECT title, mood, audio_s3_key, art_s3_key, lyrics
             FROM aria_tracks WHERE id = %s AND user_id = %s""",
        (ref_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="track not found")
    mood = (row.get("mood") or "").title() or None
    return {
        "kind": "aria_track",
        "kicker": "ARIA",
        "title": row.get("title") or "An Aria track",
        "subtitle": f"{mood} · AI music" if mood else "AI music",
        "description": _truncate(row.get("lyrics")) or "An AI-generated track on Aria.",
        "body": None,
        "media_type": "audio",
        "media_url": _key_to_url(row.get("audio_s3_key")),
        "image_url": _key_to_url(row.get("art_s3_key")),
    }


def _build_aria_podcast(user_id: str, ref_id: str) -> dict:
    row = _fetch_one(
        """SELECT title, description, audio_s3_key, art_s3_key,
                  host_a_name, host_b_name
             FROM aria_podcasts WHERE id = %s AND user_id = %s""",
        (ref_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="podcast not found")
    hosts = " & ".join(h for h in (row.get("host_a_name"), row.get("host_b_name")) if h)
    return {
        "kind": "aria_podcast",
        "kicker": "ARIA",
        "title": row.get("title") or "An Aria podcast",
        "subtitle": hosts or "AI podcast",
        "description": _truncate(row.get("description")) or "An AI-generated podcast on Aria.",
        "body": None,
        "media_type": "audio",
        "media_url": _key_to_url(row.get("audio_s3_key")),
        "image_url": _key_to_url(row.get("art_s3_key")),
    }


# ── Card builders (HEALTH / FINANCE) ─────────────────────────────────────────

def _build_card(kind: str, highlight: Optional[dict], token: str) -> dict:
    """Render a privacy-preserving highlight card. NO raw metrics are read here —
    the caller supplies only the headline/caption text it chose to publish."""
    highlight = highlight or {}
    headline = (highlight.get("headline") or "").strip()
    if not headline:
        raise HTTPException(status_code=400, detail="highlight.headline is required")
    caption = (highlight.get("caption") or "").strip()
    kicker = "HEALTH" if kind == "health_card" else "FINANCE"

    # Reuse the on-brand Calm-Intelligence card renderer (Pillow, never raises).
    from private_internet.content.cover_art import render_cover

    png = render_cover(
        1200, 630, title=headline, kicker=kicker, subtitle=caption, seed=token
    )
    image_url = AssetStore().upload_share_card(png, token)

    return {
        "kind": kind,
        "kicker": kicker,
        "title": headline,
        "subtitle": caption or None,
        "description": caption or headline,
        "body": None,
        "media_type": "card",
        "media_url": None,
        "image_url": image_url,
    }
