-- Apply before deploying the opt-in connectionVersion=2 backend.
-- No existing authorization rows are changed or reactivated.
CREATE TABLE IF NOT EXISTS echo_value_link_states (
 stage TEXT NOT NULL, subject_hash TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('linked','unlinked')),
 occurred_at INTEGER NOT NULL, household TEXT, generation TEXT,
 source TEXT NOT NULL CHECK(source IN ('event','token')),
 PRIMARY KEY(stage,subject_hash)
);
CREATE TABLE IF NOT EXISTS echo_value_widget_connections (
 stage TEXT NOT NULL, subject_hash TEXT NOT NULL, device_id TEXT NOT NULL,
 instance_id TEXT NOT NULL, package_id TEXT NOT NULL, control_key TEXT NOT NULL,
 active INTEGER NOT NULL DEFAULT 1, seen_at INTEGER NOT NULL,
 pending INTEGER NOT NULL DEFAULT 0, attempt_at INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(stage,subject_hash,device_id,instance_id,package_id)
);
CREATE INDEX IF NOT EXISTS echo_value_connection_pending
 ON echo_value_widget_connections(stage,package_id,active,pending);
