-- 0007_memory_language.sql
-- Add a detected-language column to memories so the SIGNAL pipeline can resolve
-- a topic cluster's dominant language deterministically (content/language_resolver.py)
-- without re-scanning text on read. BCP-47 code ('ar','de','en','ru','fr',…);
-- NULL = unknown / low-confidence detection. Detected at save time
-- (memory/service.py). Additive only — does not modify existing rows.
ALTER TABLE memories ADD COLUMN IF NOT EXISTS language VARCHAR(10);
