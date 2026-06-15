-- 0012_pulse_post_format.sql
-- PULSE post-generation rewrite (research-backed storytelling formats).
-- Records which of the six formats the generator chose for each post, enabling
-- future analysis of which formats perform best per mood/topic.
-- Mirrored idempotently at API startup in content/db.py::init_content_db().
-- Idempotent — safe to run at every API startup.

ALTER TABLE content_posts ADD COLUMN IF NOT EXISTS post_format VARCHAR(50);
