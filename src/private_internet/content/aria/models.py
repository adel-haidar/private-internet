"""ARIA Pydantic response models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator

AriaMood = Literal["calm", "focus", "energetic", "melancholic", "uplifting", "tense"]
TrackStatus = Literal["generating", "ready", "failed"]


class TrackOut(BaseModel):
    id: str
    user_id: str
    title: str
    mood: AriaMood
    genre: str = ""
    topic_category: str = ""
    duration_seconds: Optional[int] = None
    status: TrackStatus
    # CloudFront URLs derived from s3 keys by the router
    audio_url: Optional[str] = None
    waveform_url: Optional[str] = None
    art_url: Optional[str] = None
    lyrics: Optional[str] = None
    bpm: Optional[int] = None
    musical_key: Optional[str] = None
    instruments: list[str] = []
    brain_topic_ids: list[str] = []
    is_liked: bool = False
    created_at: datetime
    updated_at: datetime

    @field_validator("user_id", "id", mode="before")
    @classmethod
    def coerce_uuid(cls, v):
        return str(v) if v is not None else v

    @field_validator("brain_topic_ids", mode="before")
    @classmethod
    def coerce_brain_topic_ids(cls, v):
        if v is None:
            return []
        return [str(x) for x in v]

    @field_validator("instruments", mode="before")
    @classmethod
    def coerce_instruments(cls, v):
        if v is None:
            return []
        return list(v)


class PlaylistOut(BaseModel):
    id: str
    user_id: str
    title: str
    dominant_mood: Optional[AriaMood] = None
    art_url: Optional[str] = None
    track_count: int = 0
    total_duration: int = 0
    is_auto_generated: bool = False
    tracks: Optional[list[TrackOut]] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("user_id", "id", mode="before")
    @classmethod
    def coerce_uuid(cls, v):
        return str(v) if v is not None else v


class LibraryOut(BaseModel):
    tracks: list[TrackOut]
    playlists: list[PlaylistOut]
    liked_count: int
    total_tracks: int


class PlayRequest(BaseModel):
    track_id: str
    play_id: Optional[str] = None  # client-generated; server generates if absent


class PlayResponse(BaseModel):
    play_id: str
    track: TrackOut


class PlayEndRequest(BaseModel):
    play_id: str
    play_duration_seconds: int


class LikeRequest(BaseModel):
    track_id: str
    liked: bool  # True = like, False = unlike


class LikeResponse(BaseModel):
    track_id: str
    liked: bool


class SearchResponse(BaseModel):
    query: str
    tracks: list[TrackOut]


class QueueNextResponse(BaseModel):
    track: Optional[TrackOut] = None
    reason: str  # which tier was used


class GenerationStatusOut(BaseModel):
    generating: int = 0
    ready: int = 0
    failed: int = 0
    total: int = 0
