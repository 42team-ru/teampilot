ALTER TABLE teams
    ADD COLUMN IF NOT EXISTS reminder_max_per_task_per_day INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS reminder_quiet_hours_start INTEGER NOT NULL DEFAULT 22,
    ADD COLUMN IF NOT EXISTS reminder_quiet_hours_end INTEGER NOT NULL DEFAULT 9,
    ADD COLUMN IF NOT EXISTS stale_reminder_hours INTEGER NOT NULL DEFAULT 24,
    ADD COLUMN IF NOT EXISTS deadline_reminder_minutes_before INTEGER NOT NULL DEFAULT 120;

CREATE TABLE IF NOT EXISTS notification_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    batch_id UUID NOT NULL,
    task_id UUID NOT NULL REFERENCES tasks(id),
    recipient_telegram_id BIGINT,
    type VARCHAR(40) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_notification_logs_task_type_sent_at
    ON notification_logs(task_id, type, sent_at);

CREATE INDEX IF NOT EXISTS idx_notification_logs_batch_id
    ON notification_logs(batch_id);
