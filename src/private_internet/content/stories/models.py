"""Pydantic response models for the STORIES API."""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel


# ── Films ────────────────────────────────────────────────────────────────────

class FilmSummary(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    premise: Optional[str] = None
    category: Optional[str] = None
    thumbnail_url: Optional[str] = None
    poster_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: Literal["generating", "ready", "failed"]
    created_at: datetime
    updated_at: datetime


class WatchProgressOut(BaseModel):
    content_type: str
    content_id: UUID
    position_seconds: float
    duration_seconds: Optional[float] = None
    completed: bool
    last_watched_at: datetime


class FilmDetail(FilmSummary):
    """Full film detail including media URLs and watch progress."""
    signal_video_id: Optional[str] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    watch_progress: Optional[WatchProgressOut] = None
    related: List[FilmSummary] = []
    liked: bool = False


# ── Series ───────────────────────────────────────────────────────────────────

class SeriesSummary(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    premise: Optional[str] = None
    category: Optional[str] = None
    poster_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: Literal["generating", "ready", "failed"]
    created_at: datetime
    updated_at: datetime


class EpisodeSummary(BaseModel):
    id: UUID
    user_id: UUID
    series_id: UUID
    season_number: int
    episode_number: int
    title: str
    premise: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    status: Literal["generating", "ready", "failed"]
    created_at: datetime
    updated_at: datetime


class SeriesDetail(SeriesSummary):
    """Series detail without inline episodes (use /series/{id}/episodes)."""
    error_message: Optional[str] = None
    episode_count: int = 0
    liked: bool = False


# ── Categories ───────────────────────────────────────────────────────────────

class CategoryOut(BaseModel):
    category: str
    film_count: int
    series_count: int


# ── Watch progress (request/response) ────────────────────────────────────────

class WatchProgressIn(BaseModel):
    content_type: Literal["film", "episode"]
    content_id: UUID
    position_seconds: float
    duration_seconds: Optional[float] = None


# ── Like ─────────────────────────────────────────────────────────────────────

class LikeIn(BaseModel):
    content_type: Literal["film", "series", "episode"]
    content_id: UUID
    liked: bool  # True = like, False = unlike


class LikeOut(BaseModel):
    content_type: str
    content_id: UUID
    liked: bool


# ── Continue watching ────────────────────────────────────────────────────────

class ContinueWatchingItem(BaseModel):
    """Progress row enriched with the content title (fetched from film/episode tables)."""
    content_type: str
    content_id: UUID
    title: Optional[str] = None
    thumbnail_url: Optional[str] = None
    position_seconds: float
    duration_seconds: Optional[float] = None
    completed: bool
    last_watched_at: datetime


# ── Library (GET /) ──────────────────────────────────────────────────────────

class LibraryOut(BaseModel):
    films: List[FilmSummary]
    series: List[SeriesSummary]
    categories: List[CategoryOut]
    continue_watching: List[ContinueWatchingItem]


# ── Status ───────────────────────────────────────────────────────────────────

class StatusCountsOut(BaseModel):
    films: dict
    series: dict


# ── Search ───────────────────────────────────────────────────────────────────

class SearchOut(BaseModel):
    films: List[FilmSummary]
    series: List[SeriesSummary]


# ── Film generate request ────────────────────────────────────────────────────

class GenerateFilmIn(BaseModel):
    title: str
    premise: Optional[str] = None
    category: Optional[str] = None
    topic_id: Optional[str] = None  # pin to a specific SIGNAL topic
