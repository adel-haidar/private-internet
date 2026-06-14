-- 0009_job_matches_user_scope.sql
-- Make job_matches per-user so the job-hunt module is multi-tenant (test phase
-- opens it to all users; pro-gate at prod). The same job_url can now belong to
-- multiple users, so uniqueness is (user_id, job_url) instead of job_url alone.
-- The agents job module also applies this idempotently in db.py::_DDL at startup.

ALTER TABLE job_matches ADD COLUMN IF NOT EXISTS user_id UUID;
ALTER TABLE job_matches DROP CONSTRAINT IF EXISTS job_matches_job_url_key;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_job_user_url') THEN
        ALTER TABLE job_matches ADD CONSTRAINT uq_job_user_url UNIQUE (user_id, job_url);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_jm_user ON job_matches (user_id);
