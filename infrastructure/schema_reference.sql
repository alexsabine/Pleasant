-- REFERENCE CONTRACT, not an automatic Wagtail/Django migration.
-- Implement equivalent tables using Django migrations to avoid fighting Wagtail models.
-- PostgreSQL 16 + PostGIS. Public users are NOT direct database users.
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE gis_source (
  id text PRIMARY KEY,
  authority text NOT NULL,
  landing_url text NOT NULL,
  license_identifier text NOT NULL,
  permission_status text NOT NULL CHECK (permission_status IN
    ('approved','conditional','blocked','pending')),
  acquisition_date date,
  source_vintage text,
  source_crs text,
  attribution text,
  evidence_of_approval text,
  last_reviewed_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE resource (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text NOT NULL DEFAULT '',
  category text NOT NULL,
  community text NOT NULL,
  min_age integer CHECK(min_age BETWEEN 0 AND 18),
  max_age integer CHECK(max_age BETWEEN 0 AND 18),
  cost_usd numeric(9,2) CHECK(cost_usd >= 0),
  cost_status text NOT NULL DEFAULT 'unknown'
    CHECK(cost_status IN ('free','priced','variable','unknown')),
  accessibility_status text NOT NULL DEFAULT 'unknown'
    CHECK(accessibility_status IN ('verified_yes','verified_no','unknown')),
  location geography(Point, 4326),
  h3_res_8 text, -- derived only, nullable; NOT a substitute for exact location
  public_source_url text,
  website_url text,
  phone_public text,
  source_id text REFERENCES gis_source(id),
  last_verified_at timestamptz,
  last_material_change_at timestamptz,
  workflow_status text NOT NULL DEFAULT 'draft'
    CHECK(workflow_status IN ('draft','submitted','approved','archived')),
  visibility text NOT NULL DEFAULT 'public'
    CHECK(visibility IN ('public','restricted','private')),
  is_sensitive boolean NOT NULL DEFAULT false,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (min_age IS NULL OR max_age IS NULL OR min_age <= max_age)
);
CREATE INDEX resource_location_gist ON resource USING GIST(location);
CREATE INDEX resource_filters_idx ON resource(category,community,cost_status,workflow_status);

CREATE TABLE resource_claim (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resource_id uuid NOT NULL REFERENCES resource(id),
  attribute_name text NOT NULL,
  raw_value jsonb NOT NULL,
  epistemic_type text NOT NULL
    CHECK(epistemic_type IN ('observed','reported','inferred','generated','simulated')),
  source_uri text,
  source_id text REFERENCES gis_source(id),
  source_revision text,
  source_observed_at timestamptz,
  received_at timestamptz NOT NULL DEFAULT now(),
  verification_status text NOT NULL DEFAULT 'unverified'
    CHECK(verification_status IN ('unverified','verified','rejected','superseded')),
  access_level text NOT NULL DEFAULT 'restricted'
    CHECK(access_level IN ('public','restricted','private')),
  supports_publication boolean NOT NULL DEFAULT false
);
CREATE INDEX claims_by_resource ON resource_claim(resource_id,attribute_name);

CREATE TABLE resource_revision (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resource_id uuid NOT NULL REFERENCES resource(id),
  version integer NOT NULL,
  approved_claim_ids uuid[] NOT NULL DEFAULT ARRAY[]::uuid[],
  change_summary text,
  reviewer_user_id text,
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(resource_id,version)
);

CREATE TABLE community_event (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  resource_id uuid REFERENCES resource(id),
  title text NOT NULL,
  start_at timestamptz NOT NULL,
  end_at timestamptz,
  recurrence_rule text,
  timezone_name text NOT NULL DEFAULT 'America/Los_Angeles',
  location geography(Point,4326),
  source_url text,
  status text NOT NULL DEFAULT 'draft'
    CHECK(status IN ('draft','approved','cancelled','expired','archived')),
  last_verified_at timestamptz,
  CHECK(end_at IS NULL OR end_at >= start_at)
);

CREATE TABLE content_submission (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  target_resource_id uuid REFERENCES resource(id),
  submitter_user_id text,
  proposed_payload jsonb NOT NULL,
  status text NOT NULL DEFAULT 'pending'
    CHECK(status IN ('pending','approved','rejected','needs_clarification')),
  review_note text,
  submitted_at timestamptz NOT NULL DEFAULT now(),
  reviewed_at timestamptz
);

CREATE TABLE coordination_action (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  idempotency_key text NOT NULL UNIQUE,
  requester_user_id text NOT NULL,
  purpose text NOT NULL,
  source_resource_version text,
  policy_version text NOT NULL,
  status text NOT NULL DEFAULT 'draft'
    CHECK(status IN ('draft','awaiting_approval','approved','sent','failed','cancelled')),
  approved_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

-- All private records, authentication, object-level access, moderation, retention,
-- audit redaction and encryption policies MUST be implemented independently;
-- this reference schema is not a production privacy/security system.
