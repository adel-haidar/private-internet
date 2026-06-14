-- 0010_aria.sql
-- ARIA: private AI music platform tables.
-- Idempotent: CREATE TABLE IF NOT EXISTS + ADD COLUMN IF NOT EXISTS guards.
-- All user-data tables have user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE.
-- Run at API startup by aria/db.py::init_aria_db(); also kept here for the
-- database-agent and manual deploys.

-- ── Mood enum ─────────────────────────────────────────────────────────────────
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'aria_mood') THEN
        CREATE TYPE aria_mood AS ENUM (
            'calm', 'focus', 'energetic', 'melancholic', 'uplifting', 'tense'
        );
    END IF;
END $$;

-- ── aria_tracks ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aria_tracks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title            TEXT NOT NULL,
    mood             aria_mood NOT NULL,
    genre            TEXT NOT NULL DEFAULT '',
    topic_category   TEXT NOT NULL DEFAULT '',
    duration_seconds INT,
    status           VARCHAR(16) NOT NULL DEFAULT 'generating',
                     -- generating | ready | failed
    audio_s3_key     TEXT,
    waveform_s3_key  TEXT,
    art_s3_key       TEXT,
    lyrics           TEXT,
    bpm              INT,
    musical_key      TEXT,
    instruments      TEXT[],
    brain_topic_ids  UUID[],
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_aria_tracks_user_id
    ON aria_tracks(user_id);
CREATE INDEX IF NOT EXISTS idx_aria_tracks_user_mood
    ON aria_tracks(user_id, mood);
CREATE INDEX IF NOT EXISTS idx_aria_tracks_user_status
    ON aria_tracks(user_id, status);
CREATE INDEX IF NOT EXISTS idx_aria_tracks_user_created
    ON aria_tracks(user_id, created_at DESC);

-- ── aria_playlists ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aria_playlists (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title            TEXT NOT NULL,
    dominant_mood    aria_mood,
    art_s3_key       TEXT,
    track_count      INT NOT NULL DEFAULT 0,
    total_duration   INT NOT NULL DEFAULT 0,
    is_auto_generated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_aria_playlists_user_id
    ON aria_playlists(user_id);
CREATE INDEX IF NOT EXISTS idx_aria_playlists_user_mood
    ON aria_playlists(user_id, dominant_mood);

-- ── aria_playlist_tracks ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aria_playlist_tracks (
    playlist_id  UUID NOT NULL REFERENCES aria_playlists(id) ON DELETE CASCADE,
    track_id     UUID NOT NULL REFERENCES aria_tracks(id) ON DELETE CASCADE,
    position     INT NOT NULL DEFAULT 0,
    PRIMARY KEY (playlist_id, track_id)
);
CREATE INDEX IF NOT EXISTS idx_aria_pt_track
    ON aria_playlist_tracks(track_id);

-- ── aria_liked_tracks ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aria_liked_tracks (
    user_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track_id  UUID NOT NULL REFERENCES aria_tracks(id) ON DELETE CASCADE,
    liked_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, track_id)
);
CREATE INDEX IF NOT EXISTS idx_aria_liked_user
    ON aria_liked_tracks(user_id, liked_at DESC);

-- ── aria_play_history ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS aria_play_history (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track_id              UUID NOT NULL REFERENCES aria_tracks(id) ON DELETE CASCADE,
    started_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at              TIMESTAMPTZ,
    play_duration_seconds INT
);
CREATE INDEX IF NOT EXISTS idx_aria_play_user_track
    ON aria_play_history(user_id, track_id);
CREATE INDEX IF NOT EXISTS idx_aria_play_user_started
    ON aria_play_history(user_id, started_at DESC);
