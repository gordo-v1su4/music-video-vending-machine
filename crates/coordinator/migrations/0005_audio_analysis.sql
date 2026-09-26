-- One immutable analysis identity per source asset. Provider receipts survive
-- browser/coordinator restarts and never grant creative approval.
CREATE TABLE audio_analysis_jobs (
    id uuid PRIMARY KEY,
    asset_id uuid NOT NULL UNIQUE REFERENCES assets(id),
    project_id uuid NOT NULL REFERENCES projects(id),
    sha256 text NOT NULL,
    duration_ms bigint NOT NULL CHECK (duration_ms > 0),
    provider_origin text NOT NULL,
    provider_id text,
    status text NOT NULL CHECK (status IN ('queued','submitting','running','completed','failed','reconciliation_required')),
    stage text NOT NULL,
    message text,
    result jsonb,
    receipt jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    next_poll_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
CREATE INDEX audio_analysis_pending ON audio_analysis_jobs(next_poll_at)
WHERE status IN ('queued','submitting','running');
