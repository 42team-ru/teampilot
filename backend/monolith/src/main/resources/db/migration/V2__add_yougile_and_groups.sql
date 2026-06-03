ALTER TABLE users ADD COLUMN IF NOT EXISTS yougile_user_id VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS yougile_display_name VARCHAR(255);

CREATE TABLE IF NOT EXISTS chat_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    chat_id BIGINT NOT NULL UNIQUE,
    chat_title VARCHAR(255),
    added_by_telegram_id BIGINT NOT NULL,
    yougile_token VARCHAR(512) NOT NULL,
    yougile_board_id VARCHAR(255) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);
