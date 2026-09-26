CREATE INDEX operator_sessions_expiry ON operator_sessions (expires_at);
CREATE INDEX operator_sessions_revocation ON operator_sessions (revoked_at) WHERE revoked_at IS NOT NULL;
