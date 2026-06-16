-- Migration 0015: per-user generated personas for the PULSE pipeline.
--
-- content_creators gains an optional user_id column:
--   NULL  = global "basic" persona available to everyone (the shared defaults)
--   non-NULL = a persona generated specifically for that user's brain
--
-- Creator selection in creator_selector.py is updated to match:
--   WHERE is_active AND (user_id = <caller> OR user_id IS NULL)

ALTER TABLE content_creators
    ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_creators_user_id
    ON content_creators(user_id);
