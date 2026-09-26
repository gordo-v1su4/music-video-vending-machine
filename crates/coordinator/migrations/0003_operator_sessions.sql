CREATE TABLE operator_sessions (
    id uuid PRIMARY KEY,
    token_hash bytea NOT NULL UNIQUE CHECK (octet_length(token_hash) = 32),
    issuer_hash bytea NOT NULL CHECK (octet_length(issuer_hash) = 32),
    client_label text NOT NULL CHECK (length(client_label) BETWEEN 1 AND 80),
    created_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz,
    CHECK (expires_at > created_at)
);
CREATE INDEX operator_sessions_issuer ON operator_sessions (issuer_hash);
