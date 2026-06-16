-- 0017: Subscription tiers free / pro / max
--
-- Mirrors core/saas_migration.py (the repo's bootstrap-at-startup convention).
-- Earlier builds seeded plan_limits with free/personal/pro; this reconciles the
-- tiers to free/pro/max, forward-migrates any 'personal' users to 'pro', and
-- keeps quotas current. Feature access itself is gated in billing/plans.py.

-- Reconcile plan_limits quotas (free has no SIGNAL/video generation → 0 videos).
INSERT INTO plan_limits
    (plan, max_memories, max_posts_per_week, max_videos_per_week,
     max_storage_mb, content_generation_enabled)
VALUES
    ('free',  500,  10,  0,   1024,  TRUE),
    ('pro',   5000, 50,  10,  10240, TRUE),
    ('max',   NULL, NULL, NULL, NULL, TRUE)
ON CONFLICT (plan) DO UPDATE SET
    max_memories               = EXCLUDED.max_memories,
    max_posts_per_week         = EXCLUDED.max_posts_per_week,
    max_videos_per_week        = EXCLUDED.max_videos_per_week,
    max_storage_mb             = EXCLUDED.max_storage_mb,
    content_generation_enabled = EXCLUDED.content_generation_enabled;

-- Forward-migrate the obsolete 'personal' tier.
UPDATE users SET plan = 'pro' WHERE plan = 'personal';
DELETE FROM plan_limits WHERE plan = 'personal';
