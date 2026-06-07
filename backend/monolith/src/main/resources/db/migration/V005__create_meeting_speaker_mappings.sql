CREATE TABLE IF NOT EXISTS meeting_speaker_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID NOT NULL REFERENCES meetings(id),
    speaker_label VARCHAR(40) NOT NULL,
    team_user_id UUID REFERENCES team_users(id),
    mapped_by_telegram_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ,
    CONSTRAINT uk_meeting_speaker_label UNIQUE (meeting_id, speaker_label)
);

CREATE INDEX IF NOT EXISTS idx_meeting_speaker_mappings_meeting_id
    ON meeting_speaker_mappings(meeting_id);
