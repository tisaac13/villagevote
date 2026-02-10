-- Migration 004: Add vote ingestion support
-- Adds lis_member_id for Senate vote matching, and indexes for roll call vote ingestion

-- Senate vote XML identifies senators by LIS ID (e.g. "S354"), not bioguide_id
ALTER TABLE officials ADD COLUMN IF NOT EXISTS lis_member_id text;
CREATE INDEX IF NOT EXISTS idx_officials_lis_member_id ON officials(lis_member_id);

-- Unique constraint on vote_events.external_id for idempotent roll call ingestion
CREATE UNIQUE INDEX IF NOT EXISTS ux_vote_events_external_id
    ON vote_events(external_id) WHERE external_id IS NOT NULL;

-- Composite index for efficient vote event lookups by measure + body
CREATE INDEX IF NOT EXISTS idx_vote_events_measure_body
    ON vote_events(measure_id, body);
