-- 0011_stories.sql
-- STORIES module: films, series/episodes, watch progress, likes.
-- All user-data tables carry user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE.
-- content_creators is shared (no user_id), films reference it optionally.
-- Status enum: generating | ready | failed  (stored as VARCHAR with a CHECK constraint).
-- Idempotent — safe to run at every API startup.

-- ── stories_films ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stories_films (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    premise     TEXT,
    category    VARCHAR(64),
    -- source video from the SIGNAL pipeline (content_videos.id) — optional link
    signal_video_id TEXT,
    video_url   TEXT,
    thumbnail_url TEXT,
    poster_url  TEXT,
    duration_seconds FLOAT,
    status      VARCHAR(16) NOT NULL DEFAULT 'generating'
                    CHECK (status IN ('generating', 'ready', 'failed')),
    error_message TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stories_films_user_id
    ON stories_films (user_id);
CREATE INDEX IF NOT EXISTS idx_stories_films_user_category
    ON stories_films (user_id, category);
CREATE INDEX IF NOT EXISTS idx_stories_films_user_status
    ON stories_films (user_id, status);
CREATE INDEX IF NOT EXISTS idx_stories_films_user_created
    ON stories_films (user_id, created_at DESC);

-- ── stories_series ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stories_series (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    premise     TEXT,
    category    VARCHAR(64),
    poster_url  TEXT,
    thumbnail_url TEXT,
    status      VARCHAR(16) NOT NULL DEFAULT 'generating'
                    CHECK (status IN ('generating', 'ready', 'failed')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_stories_series_user_id
    ON stories_series (user_id);
CREATE INDEX IF NOT EXISTS idx_stories_series_user_category
    ON stories_series (user_id, category);

-- ── stories_episodes ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stories_episodes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    series_id       UUID NOT NULL REFERENCES stories_series(id) ON DELETE CASCADE,
    season_number   INT NOT NULL DEFAULT 1,
    episode_number  INT NOT NULL,
    title           TEXT NOT NULL,
    premise         TEXT,
    signal_video_id TEXT,
    video_url       TEXT,
    thumbnail_url   TEXT,
    duration_seconds FLOAT,
    status          VARCHAR(16) NOT NULL DEFAULT 'generating'
                        CHECK (status IN ('generating', 'ready', 'failed')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (series_id, season_number, episode_number)
);

CREATE INDEX IF NOT EXISTS idx_stories_episodes_series
    ON stories_episodes (series_id, season_number, episode_number);
CREATE INDEX IF NOT EXISTS idx_stories_episodes_user_id
    ON stories_episodes (user_id);

-- ── stories_watch_progress ───────────────────────────────────────────────────
-- content_type: 'film' | 'episode'
-- completed is derived: position_seconds >= 0.9 * duration_seconds (set by app layer)
CREATE TABLE IF NOT EXISTS stories_watch_progress (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type    VARCHAR(16) NOT NULL CHECK (content_type IN ('film', 'episode')),
    content_id      UUID NOT NULL,
    position_seconds FLOAT NOT NULL DEFAULT 0,
    duration_seconds FLOAT,
    completed       BOOLEAN NOT NULL DEFAULT FALSE,
    last_watched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, content_type, content_id)
);

CREATE INDEX IF NOT EXISTS idx_stories_wp_user_type
    ON stories_watch_progress (user_id, content_type);
CREATE INDEX IF NOT EXISTS idx_stories_wp_continue
    ON stories_watch_progress (user_id, completed, last_watched_at DESC)
    WHERE completed = FALSE;

-- ── stories_liked ────────────────────────────────────────────────────────────
-- content_type: 'film' | 'series' | 'episode'
CREATE TABLE IF NOT EXISTS stories_liked (
    user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type VARCHAR(16) NOT NULL CHECK (content_type IN ('film', 'series', 'episode')),
    content_id   UUID NOT NULL,
    liked_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, content_type, content_id)
);

CREATE INDEX IF NOT EXISTS idx_stories_liked_user
    ON stories_liked (user_id, content_type);
