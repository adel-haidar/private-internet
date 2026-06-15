-- 0014_aria_suno.sql
-- ARIA: Suno generation provenance.
-- Suno (sunoapi.org) replaces ElevenLabs as the ARIA music provider.
-- Idempotent: ADD COLUMN IF NOT EXISTS. Mirrored at startup by
-- aria/db.py::init_aria_db().

ALTER TABLE aria_tracks
    ADD COLUMN IF NOT EXISTS suno_job_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS generation_provider VARCHAR(50) DEFAULT 'suno';

-- suno_job_id: the Suno taskId, stored for debugging / potential re-download.
-- generation_provider: future-proofs provider switching (default 'suno').
