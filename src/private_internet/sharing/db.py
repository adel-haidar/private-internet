"""Sharing database helpers — psycopg2, mirrors the 0021 migration.

The public render path reads ONLY this table (a denormalised snapshot), so it
never joins user-scoped content tables and cannot leak a neighbouring row.
"""

from typing import Optional

import psycopg2.extras

from private_internet.database import _connect


def init_shares_db() -> None:
    """Create content_shares if absent. Idempotent; mirrors 0021_content_shares.sql."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS content_shares (
                token       TEXT PRIMARY KEY,
                user_id     UUID NOT NULL,
                kind        VARCHAR(32) NOT NULL,
                ref_id      TEXT,
                snapshot    JSONB NOT NULL,
                revoked     BOOLEAN NOT NULL DEFAULT FALSE,
                view_count  INT NOT NULL DEFAULT 0,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_content_shares_user "
            "ON content_shares (user_id, created_at DESC)"
        )
        conn.commit()
    finally:
        conn.close()


def create_share(
    *, token: str, user_id: str, kind: str, ref_id: Optional[str], snapshot: dict
) -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO content_shares (token, user_id, kind, ref_id, snapshot)
               VALUES (%s, %s, %s, %s, %s)""",
            (token, user_id, kind, ref_id, psycopg2.extras.Json(snapshot)),
        )
        conn.commit()
    finally:
        conn.close()


def get_share(token: str) -> Optional[dict]:
    """Public read — returns the full row (including revoked flag) or None."""
    conn = _connect()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM content_shares WHERE token = %s", (token,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def increment_view(token: str) -> None:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE content_shares SET view_count = view_count + 1 WHERE token = %s",
            (token,),
        )
        conn.commit()
    finally:
        conn.close()


def list_shares(user_id: str) -> list[dict]:
    conn = _connect()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(
            "SELECT * FROM content_shares WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def revoke(token: str, user_id: str) -> bool:
    """Revoke a share the caller owns. Returns True if a row was updated."""
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE content_shares SET revoked = TRUE WHERE token = %s AND user_id = %s",
            (token, user_id),
        )
        updated = cur.rowcount > 0
        conn.commit()
        return updated
    finally:
        conn.close()
