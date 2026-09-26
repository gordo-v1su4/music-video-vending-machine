-- Explicitly requested, billable transcription; never automatically replay a POST.
CREATE TABLE transcription_jobs (
    id uuid PRIMARY KEY,
    asset_id uuid NOT NULL UNIQUE REFERENCES assets(id),
    project_id uuid NOT NULL REFERENCES projects(id),
    sha256 text NOT NULL,
    status text NOT NULL CHECK (status IN ('queued','running','completed','failed','reconciliation_required')),
    message text,
    result jsonb,
    receipt jsonb,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);
