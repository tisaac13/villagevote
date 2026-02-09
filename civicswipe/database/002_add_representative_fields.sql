-- Add photo_url and bioguide_id to officials table for representative lookup
ALTER TABLE officials ADD COLUMN IF NOT EXISTS photo_url text;
ALTER TABLE officials ADD COLUMN IF NOT EXISTS bioguide_id text;
CREATE INDEX IF NOT EXISTS idx_officials_bioguide_id ON officials(bioguide_id);
