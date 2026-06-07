CREATE TABLE IF NOT EXISTS courses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url VARCHAR(2048) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    thumbnail_url VARCHAR(2048),
    scope VARCHAR(20) NOT NULL,
    team_id UUID REFERENCES teams(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_courses_team_id ON courses(team_id);
CREATE INDEX IF NOT EXISTS idx_courses_scope ON courses(scope);
CREATE INDEX IF NOT EXISTS idx_courses_url ON courses(url);

ALTER TABLE tasks ADD COLUMN IF NOT EXISTS course_recommended_at TIMESTAMPTZ;
