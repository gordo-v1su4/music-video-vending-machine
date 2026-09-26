CREATE TABLE projects (
    id uuid PRIMARY KEY,
    revision bigint NOT NULL CHECK (revision >= 0),
    document jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE project_events (
    project_id uuid NOT NULL REFERENCES projects(id),
    revision bigint NOT NULL,
    document jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id, revision)
);
CREATE TABLE assets (
    id uuid PRIMARY KEY,
    project_id uuid NOT NULL REFERENCES projects(id),
    object_key text NOT NULL UNIQUE,
    metadata jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX assets_project_id ON assets(project_id);
