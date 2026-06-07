CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id),
    meeting_url VARCHAR(1024) NOT NULL,
    primary_recorder_id UUID NOT NULL REFERENCES team_users(id),
    active BOOLEAN NOT NULL DEFAULT true,
    recording_bucket VARCHAR(255),
    recording_s3_key VARCHAR(1024),
    recording_content_type VARCHAR(255),
    recording_size_bytes BIGINT,
    transcript_bucket VARCHAR(255),
    transcript_s3_key VARCHAR(1024),
    title VARCHAR(500),
    description VARCHAR(2000),
    summary TEXT,
    finalized_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_meetings_team_id ON meetings(team_id);
CREATE INDEX IF NOT EXISTS idx_meetings_primary_recorder_id ON meetings(primary_recorder_id);
