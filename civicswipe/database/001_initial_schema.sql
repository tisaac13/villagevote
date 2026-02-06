-- CivicSwipe Initial Database Schema
-- Phoenix, Arizona MVP Release
-- Requires: PostgreSQL 12+

-- ============================================================================
-- 0) Extensions
-- ============================================================================
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================================================
-- 1) Enums
-- ============================================================================
DO $$ BEGIN
  CREATE TYPE jurisdiction_level AS ENUM ('federal','state','county','city');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE measure_status AS ENUM (
    'introduced','scheduled','in_committee','passed','failed','tabled','withdrawn','unknown'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE vote_value AS ENUM ('yes','no');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE official_vote_value AS ENUM ('yea','nay','abstain','absent','present','not_voting','unknown');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE source_system AS ENUM ('congress','govinfo','openstates','legiscan','legistar','custom');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE content_type AS ENUM ('html','pdf','api','text');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE auth_provider AS ENUM ('password','google','apple');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE division_type AS ENUM (
    'country','state','county','city',
    'us_congressional_district',
    'state_upper_district','state_lower_district',
    'city_council_district'
  );
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ============================================================================
-- 2) Users + required address (privacy-safe patterns)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
  id              uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  email           citext UNIQUE,
  phone           citext UNIQUE,
  provider        auth_provider NOT NULL DEFAULT 'password',
  password_hash   text,
  created_at      timestamptz NOT NULL DEFAULT now(),
  last_login_at   timestamptz
);

CREATE TABLE IF NOT EXISTS user_profile (
  user_id            uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  
  -- Required address fields (encrypted)
  address_line1_enc  bytea NOT NULL,
  address_line2_enc  bytea,
  city               text NOT NULL,
  state              text NOT NULL,
  postal_code        text NOT NULL,
  country            text NOT NULL DEFAULT 'US',
  
  -- Geospatial matching
  lat                numeric(9,6),
  lon                numeric(9,6),
  
  -- Hash for dedup/audit
  address_hash       text NOT NULL,
  
  timezone           text NOT NULL DEFAULT 'America/Phoenix',
  updated_at         timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_user_profile_state_zip ON user_profile(state, postal_code);
CREATE INDEX IF NOT EXISTS idx_user_profile_city ON user_profile(city);
CREATE UNIQUE INDEX IF NOT EXISTS ux_user_profile_address_hash ON user_profile(address_hash);

CREATE TABLE IF NOT EXISTS user_preferences (
  user_id         uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  topics          text[] NOT NULL DEFAULT '{}',
  notify_enabled  boolean NOT NULL DEFAULT true,
  updated_at      timestamptz NOT NULL DEFAULT now()
);

-- ============================================================================
-- 3) Divisions (OCD IDs)
-- ============================================================================
CREATE TABLE IF NOT EXISTS divisions (
  id             uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  division_type  division_type NOT NULL,
  ocd_id         text,
  name           text NOT NULL,
  level          jurisdiction_level NOT NULL,
  parent_id      uuid REFERENCES divisions(id) ON DELETE SET NULL,
  
  UNIQUE (division_type, ocd_id)
);

CREATE TABLE IF NOT EXISTS user_divisions (
  user_id     uuid REFERENCES users(id) ON DELETE CASCADE,
  division_id uuid REFERENCES divisions(id) ON DELETE CASCADE,
  derived_at  timestamptz NOT NULL DEFAULT now(),
  
  PRIMARY KEY (user_id, division_id)
);

CREATE INDEX IF NOT EXISTS idx_user_divisions_user ON user_divisions(user_id);

-- ============================================================================
-- 4) Officials + mapping to divisions
-- ============================================================================
CREATE TABLE IF NOT EXISTS officials (
  id             uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  external_id    text,
  name           text NOT NULL,
  office         text,
  party          text,
  chamber        text,
  district_label text,
  updated_at     timestamptz NOT NULL DEFAULT now(),
  
  UNIQUE (external_id)
);

CREATE TABLE IF NOT EXISTS official_divisions (
  official_id uuid REFERENCES officials(id) ON DELETE CASCADE,
  division_id uuid REFERENCES divisions(id) ON DELETE CASCADE,
  role        text,
  PRIMARY KEY (official_id, division_id)
);

CREATE TABLE IF NOT EXISTS user_officials (
  user_id     uuid REFERENCES users(id) ON DELETE CASCADE,
  official_id uuid REFERENCES officials(id) ON DELETE CASCADE,
  active      boolean NOT NULL DEFAULT true,
  derived_at  timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (user_id, official_id)
);

-- ============================================================================
-- 5) Measures (bills / agenda items)
-- ============================================================================
CREATE TABLE IF NOT EXISTS measures (
  id                 uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  source             source_system NOT NULL,
  external_id        text NOT NULL,
  title              text NOT NULL,
  
  level              jurisdiction_level NOT NULL,
  division_id        uuid REFERENCES divisions(id) ON DELETE SET NULL,
  
  status             measure_status NOT NULL DEFAULT 'unknown',
  introduced_at      timestamptz,
  scheduled_for      timestamptz,
  updated_at         timestamptz NOT NULL DEFAULT now(),
  
  topic_tags         text[] NOT NULL DEFAULT '{}',
  summary_short      text,
  summary_long       text,
  
  canonical_key      text,
  
  UNIQUE (source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_measures_level_status_time ON measures(level, status, scheduled_for);
CREATE INDEX IF NOT EXISTS idx_measures_division ON measures(division_id);

CREATE TABLE IF NOT EXISTS measure_sources (
  id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  measure_id  uuid REFERENCES measures(id) ON DELETE CASCADE,
  label       text NOT NULL,
  url         text NOT NULL,
  ctype       content_type NOT NULL DEFAULT 'html',
  is_primary  boolean NOT NULL DEFAULT false
);

CREATE TABLE IF NOT EXISTS measure_status_events (
  id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  measure_id    uuid REFERENCES measures(id) ON DELETE CASCADE,
  status        measure_status NOT NULL,
  effective_at  timestamptz NOT NULL,
  source_url    text,
  raw_ref       text
);

CREATE INDEX IF NOT EXISTS idx_measure_status_events_measure ON measure_status_events(measure_id, effective_at DESC);

-- ============================================================================
-- 6) Vote events + official roll calls
-- ============================================================================
CREATE TABLE IF NOT EXISTS vote_events (
  id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  measure_id    uuid REFERENCES measures(id) ON DELETE CASCADE,
  
  body          text NOT NULL,
  external_id   text,
  
  scheduled_for timestamptz,
  held_at       timestamptz,
  result        measure_status NOT NULL DEFAULT 'unknown',
  
  updated_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_vote_events_measure ON vote_events(measure_id);
CREATE INDEX IF NOT EXISTS idx_vote_events_held_at ON vote_events(held_at DESC);

CREATE TABLE IF NOT EXISTS official_votes (
  vote_event_id uuid REFERENCES vote_events(id) ON DELETE CASCADE,
  official_id   uuid REFERENCES officials(id) ON DELETE CASCADE,
  vote          official_vote_value NOT NULL DEFAULT 'unknown',
  PRIMARY KEY (vote_event_id, official_id)
);

-- ============================================================================
-- 7) User swipes + match results
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_votes (
  id          uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id     uuid REFERENCES users(id) ON DELETE CASCADE,
  measure_id  uuid REFERENCES measures(id) ON DELETE CASCADE,
  vote        vote_value NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now(),
  
  UNIQUE (user_id, measure_id)
);

CREATE INDEX IF NOT EXISTS idx_user_votes_user_created ON user_votes(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS match_results (
  user_id       uuid REFERENCES users(id) ON DELETE CASCADE,
  measure_id    uuid REFERENCES measures(id) ON DELETE CASCADE,
  
  computed_at   timestamptz NOT NULL DEFAULT now(),
  match_score   numeric(4,3) NOT NULL DEFAULT 0.000,
  breakdown     jsonb NOT NULL DEFAULT '{}'::jsonb,
  notes         text,
  
  PRIMARY KEY (user_id, measure_id)
);

-- ============================================================================
-- 8) Ingestion plumbing
-- ============================================================================
CREATE TABLE IF NOT EXISTS connectors (
  id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  name          text NOT NULL,
  source        source_system NOT NULL,
  enabled       boolean NOT NULL DEFAULT true,
  config        jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at    timestamptz NOT NULL DEFAULT now(),
  
  UNIQUE (name)
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
  id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  connector_id  uuid REFERENCES connectors(id) ON DELETE CASCADE,
  started_at    timestamptz NOT NULL DEFAULT now(),
  finished_at   timestamptz,
  status        text NOT NULL DEFAULT 'running',
  stats         jsonb NOT NULL DEFAULT '{}'::jsonb,
  error         text
);

CREATE TABLE IF NOT EXISTS raw_artifacts (
  id            uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
  connector_id  uuid REFERENCES connectors(id) ON DELETE CASCADE,
  measure_id    uuid REFERENCES measures(id) ON DELETE SET NULL,
  url           text,
  ctype         content_type,
  fetched_at    timestamptz NOT NULL DEFAULT now(),
  blob_ref      text NOT NULL,
  sha256        text
);

CREATE INDEX IF NOT EXISTS idx_raw_artifacts_measure ON raw_artifacts(measure_id, fetched_at DESC);
