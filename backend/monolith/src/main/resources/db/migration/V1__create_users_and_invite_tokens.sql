CREATE TABLE IF NOT EXISTS users
(
    id             UUID        NOT NULL PRIMARY KEY,
    telegram_id    BIGINT      NOT NULL,
    telegram_login VARCHAR(100),
    first_name     VARCHAR(100),
    last_name      VARCHAR(100),
    role           VARCHAR(50) NOT NULL DEFAULT 'USER',
    created_at     TIMESTAMP,
    updated_at     TIMESTAMP,
    CONSTRAINT uq_users_telegram_id UNIQUE (telegram_id)
);

CREATE TABLE IF NOT EXISTS invite_tokens
(
    id              UUID         NOT NULL PRIMARY KEY,
    token           VARCHAR(64)  NOT NULL,
    expires_at      TIMESTAMP    NOT NULL,
    used_at         TIMESTAMP,
    used_by_user_id UUID REFERENCES users (id),
    created_by      VARCHAR(100),
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP,
    CONSTRAINT uq_invite_token UNIQUE (token)
);
