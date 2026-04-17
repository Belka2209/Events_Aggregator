-- Convert outbox.retry_count from text/varchar to integer.
-- Safe for PostgreSQL when existing values are numeric strings.
-- Run inside a transaction.

BEGIN;

ALTER TABLE outbox
ALTER COLUMN retry_count TYPE INTEGER
USING retry_count::integer;

COMMIT;
