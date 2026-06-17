-- Global sharing: public, tokenised share links for any content item.
--
-- A share captures a DENORMALISED snapshot of the item at share time, so the
-- public render path needs no user-scoped joins, never leaks neighbouring data,
-- and is immune to the source item later being edited or deleted.
--
-- Mirrored idempotently at API startup by sharing/db.py::init_shares_db().

CREATE TABLE IF NOT EXISTS content_shares (
    token       TEXT PRIMARY KEY,
    user_id     UUID NOT NULL,                 -- the sharer (author)
    kind        VARCHAR(32) NOT NULL,          -- pulse_post|signal_video|stories_film|
                                               -- stories_episode|aria_track|aria_podcast|
                                               -- health_card|finance_card
    ref_id      TEXT,                          -- id of the underlying item (NULL for cards)
    snapshot    JSONB NOT NULL,                -- public display payload (see sharing/service.py)
    revoked     BOOLEAN NOT NULL DEFAULT FALSE,
    view_count  INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_content_shares_user ON content_shares (user_id, created_at DESC);
