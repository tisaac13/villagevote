-- Performance indexes for scalability
-- Addresses hot query paths identified in the scalability audit

-- UserOfficial: queried on every /representatives call with (user_id, active)
CREATE INDEX IF NOT EXISTS idx_user_officials_user_active
    ON user_officials(user_id, active);

-- MeasureSource: batch-loaded by measure_id in feed
CREATE INDEX IF NOT EXISTS idx_measure_sources_measure_id
    ON measure_sources(measure_id);

-- OfficialVote: queried during alignment computation
CREATE INDEX IF NOT EXISTS idx_official_votes_official_id
    ON official_votes(official_id);

-- UserVote: queried on dashboard and feed (user_id + created_at for recent activity)
CREATE INDEX IF NOT EXISTS idx_user_votes_user_created
    ON user_votes(user_id, created_at DESC);
