CREATE TABLE kanban_boards (
    id                UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    name              VARCHAR(255) NOT NULL,
    provider          VARCHAR(50)  NOT NULL,
    external_board_id VARCHAR(512) NOT NULL,
    access_token      VARCHAR(1024),
    status_mappings   TEXT,
    group_id          UUID         REFERENCES chat_groups(id),
    active            BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE tasks (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    board_id         UUID         REFERENCES kanban_boards(id),
    creator_id       UUID         NOT NULL REFERENCES users(id),
    assignee_id      UUID         REFERENCES users(id),
    title            VARCHAR(512) NOT NULL,
    description      TEXT,
    deadline         TIMESTAMPTZ,
    status           VARCHAR(50)  NOT NULL DEFAULT 'OPEN',
    external_task_id VARCHAR(512),
    external_status  VARCHAR(255),
    chat_id          BIGINT,
    source_context   TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE task_status_history (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id             UUID        NOT NULL REFERENCES tasks(id),
    previous_status     VARCHAR(50),
    new_status          VARCHAR(50) NOT NULL,
    external_status     VARCHAR(255),
    changed_by_user_id  UUID        REFERENCES users(id),
    change_source       VARCHAR(50) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tasks_board_id        ON tasks(board_id);
CREATE INDEX idx_tasks_status          ON tasks(status);
CREATE INDEX idx_tasks_external_id     ON tasks(external_task_id);
CREATE INDEX idx_task_history_task_id  ON task_status_history(task_id);
