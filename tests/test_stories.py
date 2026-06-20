"""
Unit tests for the STORIES module.

No DB, no network. The DB-backed helpers are exercised against a mocked
psycopg2 connection so the REAL production functions run (their SQL, user
scoping and Python-side merging) — not a re-implementation of that logic.
Covered:
  - Watch-progress completion at the 90 % threshold (_is_completed)
  - continue_watching: real query — user scoping, WHERE/ORDER/LIMIT clauses
  - list_categories: real Python merge of two grouped-count queries
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

from private_internet.content.stories import db as stories_db
from private_internet.content.stories.db import (
    _is_completed,
    continue_watching,
    list_categories,
)


def _rdict_conn(*fetchall_batches):
    """A MagicMock conn whose cursor.fetchall() yields each batch in turn.

    `RealDictCursor` rows behave like dicts, so plain dicts are a faithful stand-in.
    """
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.side_effect = list(fetchall_batches)
    conn.cursor.return_value = cursor
    return conn, cursor


# ── _is_completed (90% rule) ──────────────────────────────────────────────────

class TestIsCompleted:
    def test_below_threshold_not_completed(self):
        # 89 % < 90 % → not completed
        assert _is_completed(89.0, 100.0) is False

    def test_exactly_at_threshold_completed(self):
        # 90 % == 90 % → completed
        assert _is_completed(90.0, 100.0) is True

    def test_above_threshold_completed(self):
        # 95 % > 90 % → completed
        assert _is_completed(95.0, 100.0) is True

    def test_zero_position_not_completed(self):
        assert _is_completed(0.0, 100.0) is False

    def test_unknown_duration_not_completed(self):
        # If duration is None, we cannot compute completion — always False
        assert _is_completed(99.0, None) is False

    def test_zero_duration_not_completed(self):
        # Division guard: zero duration → False (avoids ZeroDivisionError)
        assert _is_completed(0.0, 0.0) is False

    def test_fractional_duration(self):
        # 27 seconds of a 30-second clip = 90 % exactly
        assert _is_completed(27.0, 30.0) is True

    def test_fractional_slightly_under(self):
        # 26.9 / 30 = 89.67 % → not completed
        assert _is_completed(26.9, 30.0) is False

    def test_full_watch_completed(self):
        # position == duration → definitely completed
        assert _is_completed(120.0, 120.0) is True

    def test_beyond_duration_completed(self):
        # position > duration (e.g. skip to end) → still completed
        assert _is_completed(125.0, 120.0) is True

    def test_short_film(self):
        # 4.5 s of a 5-second clip = 90 % exactly
        assert _is_completed(4.5, 5.0) is True

    def test_short_film_just_under(self):
        # 4.4 / 5 = 88 % → not completed
        assert _is_completed(4.4, 5.0) is False


# ── continue_watching (real query against a mocked connection) ────────────────

def _make_progress(
    *,
    content_type: str = "film",
    position_seconds: float,
    duration_seconds: float = 100.0,
    completed: bool,
    last_watched_at: datetime,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "content_type": content_type,
        "content_id": str(uuid.uuid4()),
        "position_seconds": position_seconds,
        "duration_seconds": duration_seconds,
        "completed": completed,
        "last_watched_at": last_watched_at,
    }


class TestContinueWatching:
    """Exercise the real continue_watching function. The completed/position
    filter and ordering live in SQL (the DB applies them), so the rows the mock
    returns represent what Postgres would hand back; the test pins the contract:
    user scoping is threaded into the query, the WHERE/ORDER/LIMIT clauses are
    present, and rows are surfaced unchanged as dicts."""

    def _ts(self, days_ago: int = 0) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=days_ago)

    def test_query_is_user_scoped_with_filter_order_and_limit(self):
        user_id = str(uuid.uuid4())
        rows = [_make_progress(position_seconds=50.0, completed=False, last_watched_at=self._ts())]
        conn, cursor = _rdict_conn(rows)

        result = continue_watching(conn, user_id=user_id, limit=7)

        # Rows are returned as plain dicts (RealDictCursor -> dict()).
        assert len(result) == 1
        assert result[0]["position_seconds"] == 50.0
        assert all(isinstance(r, dict) for r in result)

        sql, params = cursor.execute.call_args.args
        # The completion + position filter and ordering must be in the SQL itself
        # (this is what makes the feature correct — not a Python re-filter).
        assert "completed = FALSE" in sql
        assert "position_seconds > 30" in sql
        assert "ORDER BY last_watched_at DESC" in sql
        assert "LIMIT %s" in sql
        # MUST SCOPE BY USER — and honour the requested limit.
        assert params[0] == user_id
        assert params[-1] == 7
        # RealDictCursor was requested so rows arrive keyed by column name.
        assert cursor is conn.cursor.return_value
        assert conn.cursor.call_args.kwargs.get("cursor_factory") is stories_db.RealDictCursor

    def test_empty_result_returns_empty_list(self):
        conn, _ = _rdict_conn([])
        assert continue_watching(conn, user_id="u1") == []

    def test_default_limit_is_ten(self):
        conn, cursor = _rdict_conn([])
        continue_watching(conn, user_id="u1")
        _, params = cursor.execute.call_args.args
        assert params[-1] == 10


# ── list_categories (real Python merge of two grouped-count queries) ──────────

class TestListCategories:
    """list_categories runs two GROUP BY queries (films, series) and merges the
    counts in Python. The merge is the real logic under test here."""

    def test_merges_film_and_series_counts_user_scoped(self):
        user_id = str(uuid.uuid4())
        film_rows = [
            {"category": "drama", "film_count": 2},
            {"category": "thriller", "film_count": 1},
        ]
        series_rows = [
            {"category": "drama", "series_count": 1},
            {"category": "sci-fi", "series_count": 3},
        ]
        conn, cursor = _rdict_conn(film_rows, series_rows)

        result = list_categories(conn, user_id=user_id)
        cats = {r["category"]: r for r in result}

        # drama appears in both tables → both counts merged on one row.
        assert cats["drama"] == {"category": "drama", "film_count": 2, "series_count": 1}
        # thriller only has films; sci-fi only has series — zero-filled, not dropped.
        assert cats["thriller"] == {"category": "thriller", "film_count": 1, "series_count": 0}
        assert cats["sci-fi"] == {"category": "sci-fi", "film_count": 0, "series_count": 3}
        # Result is sorted alphabetically by category.
        assert [r["category"] for r in result] == ["drama", "sci-fi", "thriller"]

        # Both queries scoped to the user and exclude NULL categories in SQL.
        for call in cursor.execute.call_args_list:
            sql, params = call.args
            assert "category IS NOT NULL" in sql
            assert params[0] == user_id

    def test_empty_both_tables(self):
        conn, _ = _rdict_conn([], [])
        assert list_categories(conn, user_id="u1") == []

    def test_disjoint_categories_zero_fill(self):
        conn, _ = _rdict_conn(
            [{"category": "action", "film_count": 5}],
            [{"category": "comedy", "series_count": 4}],
        )
        result = list_categories(conn, user_id="u1")
        cats = {r["category"]: r for r in result}
        assert cats["action"]["series_count"] == 0
        assert cats["comedy"]["film_count"] == 0
