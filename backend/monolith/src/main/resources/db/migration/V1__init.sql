CREATE TABLE users
(
    id             UUID                        NOT NULL,
    created_at     TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated_at     TIMESTAMP WITHOUT TIME ZONE,
    username       VARCHAR(255)                NOT NULL,
    email          VARCHAR(255)                NOT NULL,
    email_verified BOOLEAN     DEFAULT FALSE   NOT NULL,
    first_name     VARCHAR(255)                NOT NULL,
    last_name      VARCHAR(255)                NOT NULL,
    password_hash  VARCHAR(255)                NOT NULL,
    active         BOOLEAN     DEFAULT TRUE    NOT NULL,
    auth_provider  VARCHAR(50) DEFAULT 'LOCAL' NOT NULL,
    CONSTRAINT pk_users PRIMARY KEY (id)
);

ALTER TABLE users ADD CONSTRAINT uc_users_email    UNIQUE (email);
ALTER TABLE users ADD CONSTRAINT uc_users_username UNIQUE (username);

CREATE TABLE user_roles
(
    user_id UUID         NOT NULL,
    roles   VARCHAR(255) NOT NULL
);

ALTER TABLE user_roles
    ADD CONSTRAINT fk_user_roles_on_user FOREIGN KEY (user_id) REFERENCES users (id);

CREATE TABLE refresh_tokens
(
    token_value VARCHAR(255)                NOT NULL,
    user_id     UUID                        NOT NULL,
    username    VARCHAR(255)                NOT NULL,
    expires_at  TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at  TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    CONSTRAINT pk_refresh_tokens PRIMARY KEY (token_value)
);
