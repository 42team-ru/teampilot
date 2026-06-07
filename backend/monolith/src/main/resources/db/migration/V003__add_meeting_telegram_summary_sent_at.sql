ALTER TABLE meetings
    ADD COLUMN IF NOT EXISTS telegram_summary_sent_at TIMESTAMPTZ;
