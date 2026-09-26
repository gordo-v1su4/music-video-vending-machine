ALTER TABLE transcription_jobs ADD COLUMN model text NOT NULL DEFAULT 'legacy-nova-3'
    CHECK (model IN ('legacy-nova-3','stack-structure-v1'));
ALTER TABLE transcription_jobs DROP CONSTRAINT transcription_jobs_asset_id_key;
ALTER TABLE transcription_jobs ADD CONSTRAINT transcription_asset_model_unique UNIQUE(asset_id, model);
