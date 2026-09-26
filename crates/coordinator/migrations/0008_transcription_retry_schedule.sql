-- An unavailable object must not monopolize the transcription queue.
ALTER TABLE transcription_jobs ADD COLUMN next_poll_at timestamptz NOT NULL DEFAULT clock_timestamp();
CREATE INDEX transcription_ready ON transcription_jobs(next_poll_at, created_at) WHERE status='queued';
