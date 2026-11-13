-- 0003-apply-rank.sql: durable operator-controlled ordering for the apply queue.
-- score remains collector-computed; apply_rank is set by the writer lane and never recomputed by ingest.
ALTER TABLE job ADD COLUMN apply_rank INTEGER;
CREATE INDEX IF NOT EXISTS idx_job_apply_rank ON job(status, apply_rank);
