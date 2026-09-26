-- An intent survives request cancellation and coordinator restart. The object
-- is promoted only after length and checksum verification; absent objects stay
-- reconcilable because an uncertain remote PUT may still finish later.
CREATE TABLE upload_intents (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id),
    object_key text NOT NULL UNIQUE,
    metadata jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    checked_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX upload_intents_checked_at ON upload_intents(checked_at,id);
