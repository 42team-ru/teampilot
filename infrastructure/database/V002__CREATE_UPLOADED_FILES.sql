CREATE TABLE IF NOT EXISTS uploaded_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bucket VARCHAR(255) NOT NULL,
    s3_key VARCHAR(1024) NOT NULL UNIQUE,
    original_filename VARCHAR(512),
    content_type VARCHAR(255),
    size_bytes BIGINT,
    owner_id UUID,
    telegram_user_id BIGINT,
    telegram_chat_id BIGINT,
    telegram_username VARCHAR(255),
    telegram_first_name VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
