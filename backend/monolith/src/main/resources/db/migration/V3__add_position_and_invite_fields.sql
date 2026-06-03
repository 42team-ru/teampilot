ALTER TABLE users ADD COLUMN position VARCHAR(255);

ALTER TABLE invite_tokens ADD COLUMN first_name VARCHAR(100);
ALTER TABLE invite_tokens ADD COLUMN last_name VARCHAR(100);
ALTER TABLE invite_tokens ADD COLUMN position VARCHAR(255);
