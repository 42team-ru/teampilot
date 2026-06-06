CREATE TABLE IF NOT EXISTS meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id UUID NOT NULL REFERENCES teams(id),
    meeting_url VARCHAR(1024) NOT NULL,
    primary_recorder_id UUID NOT NULL REFERENCES team_users(id),
    active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_meetings_team_id ON meetings(team_id);
CREATE INDEX IF NOT EXISTS idx_meetings_primary_recorder_id ON meetings(primary_recorder_id);
