"""
Pure-Python unit tests for the STORIES module.

No DB, no network — only logic that lives in Python.
Covered:
  - Watch-progress completion at the 90 % threshold (_is_completed)
  - continue_watching filter / order (pure-Python simulation)
  - category counting helper (pure-Python simulation)
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest

from private_internet.content.stories.db import _is_completed


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


# ── continue_watching (pure-Python simulation) ────────────────────────────────

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


def _simulate_continue_watching(rows: list[dict], limit: int = 10) -> list[dict]:
    """Mirror the continue_watching SQL logic in pure Python for testing."""
    filtered = [
        r for r in rows
        if not r["completed"] and r["position_seconds"] > 30
    ]
    filtered.sort(key=lambda r: r["last_watched_at"], reverse=True)
    return filtered[:limit]


class TestContinueWatching:
    def _ts(self, days_ago: int = 0) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=days_ago)

    def test_excludes_completed(self):
        rows = [
            _make_progress(position_seconds=95.0, completed=True, last_watched_at=self._ts()),
            _make_progress(position_seconds=50.0, completed=False, last_watched_at=self._ts()),
        ]
        result = _simulate_continue_watching(rows)
        assert len(result) == 1
        assert result[0]["position_seconds"] == 50.0

    def test_excludes_position_under_30(self):
        rows = [
            _make_progress(position_seconds=20.0, completed=False, last_watched_at=self._ts()),
            _make_progress(position_seconds=60.0, completed=False, last_watched_at=self._ts()),
        ]
        result = _simulate_continue_watching(rows)
        assert len(result) == 1
        assert result[0]["position_seconds"] == 60.0

    def test_excludes_exactly_30(self):
        # boundary: > 30, not >= 30
        rows = [
            _make_progress(position_seconds=30.0, completed=False, last_watched_at=self._ts()),
            _make_progress(position_seconds=31.0, completed=False, last_watched_at=self._ts()),
        ]
        result = _simulate_continue_watching(rows)
        assert len(result) == 1
        assert result[0]["position_seconds"] == 31.0

    def test_ordered_by_last_watched_desc(self):
        rows = [
            _make_progress(position_seconds=50.0, completed=False, last_watched_at=self._ts(days_ago=3)),
            _make_progress(position_seconds=60.0, completed=False, last_watched_at=self._ts(days_ago=1)),
            _make_progress(position_seconds=70.0, completed=False, last_watched_at=self._ts(days_ago=0)),
        ]
        result = _simulate_continue_watching(rows)
        positions = [r["position_seconds"] for r in result]
        assert positions == [70.0, 60.0, 50.0]

    def test_limit_applied(self):
        rows = [
            _make_progress(position_seconds=float(i * 10 + 31), completed=False, last_watched_at=self._ts(days_ago=i))
            for i in range(15)
        ]
        result = _simulate_continue_watching(rows, limit=10)
        assert len(result) == 10

    def test_empty_when_all_completed(self):
        rows = [
            _make_progress(position_seconds=95.0, completed=True, last_watched_at=self._ts())
            for _ in range(5)
        ]
        result = _simulate_continue_watching(rows)
        assert result == []

    def test_empty_list(self):
        assert _simulate_continue_watching([]) == []


# ── Category counting (pure-Python simulation) ────────────────────────────────

def _simulate_categories(
    films: list[dict], series: list[dict]
) -> list[dict]:
    """Mirror the list_categories SQL+Python merge logic."""
    film_counts: dict[str, int] = {}
    for f in films:
        cat = f.get("category")
        if cat:
            film_counts[cat] = film_counts.get(cat, 0) + 1

    series_counts: dict[str, int] = {}
    for s in series:
        cat = s.get("category")
        if cat:
            series_counts[cat] = series_counts.get(cat, 0) + 1

    all_cats = sorted(set(film_counts) | set(series_counts))
    return [
        {
            "category": cat,
            "film_count": film_counts.get(cat, 0),
            "series_count": series_counts.get(cat, 0),
        }
        for cat in all_cats
    ]


class TestCategoryCounting:
    def test_counts_films_by_category(self):
        films = [
            {"category": "drama"},
            {"category": "drama"},
            {"category": "thriller"},
        ]
        result = _simulate_categories(films, [])
        cats = {r["category"]: r for r in result}
        assert cats["drama"]["film_count"] == 2
        assert cats["thriller"]["film_count"] == 1

    def test_counts_series_by_category(self):
        series = [
            {"category": "sci-fi"},
            {"category": "sci-fi"},
            {"category": "sci-fi"},
        ]
        result = _simulate_categories([], series)
        assert result[0]["series_count"] == 3

    def test_merges_films_and_series_counts(self):
        films = [{"category": "drama"}, {"category": "thriller"}]
        series = [{"category": "drama"}, {"category": "sci-fi"}]
        result = _simulate_categories(films, series)
        cats = {r["category"]: r for r in result}
        assert cats["drama"]["film_count"] == 1
        assert cats["drama"]["series_count"] == 1
        assert cats["thriller"]["series_count"] == 0
        assert cats["sci-fi"]["film_count"] == 0

    def test_skips_null_category(self):
        films = [{"category": None}, {"category": "drama"}]
        result = _simulate_categories(films, [])
        assert len(result) == 1
        assert result[0]["category"] == "drama"

    def test_sorted_alphabetically(self):
        films = [{"category": "thriller"}, {"category": "drama"}, {"category": "action"}]
        result = _simulate_categories(films, [])
        assert [r["category"] for r in result] == ["action", "drama", "thriller"]

    def test_empty_inputs(self):
        assert _simulate_categories([], []) == []
