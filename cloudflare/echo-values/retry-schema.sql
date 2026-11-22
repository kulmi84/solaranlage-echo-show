-- Additive, opt-in registration retry pause. No existing authority rows change.
CREATE TABLE IF NOT EXISTS echo_value_widget_retries (
 stage TEXT NOT NULL, subject_hash TEXT NOT NULL, device_id TEXT NOT NULL,
 instance_id TEXT NOT NULL, package_id TEXT NOT NULL,
 failures INTEGER NOT NULL DEFAULT 0, last_attempt INTEGER NOT NULL DEFAULT 0,
 resume_at INTEGER NOT NULL DEFAULT 0, resume_household TEXT, resume_generation TEXT,
 source_stage TEXT, source_package TEXT, source_instance TEXT,
 pending INTEGER NOT NULL DEFAULT 0, attempt_at INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(stage,subject_hash,device_id,instance_id,package_id)
);
CREATE INDEX IF NOT EXISTS echo_value_retry_pending
 ON echo_value_widget_retries(stage,package_id,pending,attempt_at);
