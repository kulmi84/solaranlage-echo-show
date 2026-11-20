PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS echo_value_devices (
 stage TEXT NOT NULL, device_id TEXT NOT NULL, subject_hash TEXT NOT NULL,
 household TEXT NOT NULL REFERENCES households(id) ON DELETE CASCADE,
 generation TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
 updated_at INTEGER NOT NULL, PRIMARY KEY(stage,device_id)
);
CREATE TABLE IF NOT EXISTS echo_value_usages (
 stage TEXT NOT NULL, device_id TEXT NOT NULL, instance_id TEXT NOT NULL,
 package_id TEXT NOT NULL, subject_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
 updated_at INTEGER NOT NULL, PRIMARY KEY(stage,device_id,instance_id),
 FOREIGN KEY(stage,device_id) REFERENCES echo_value_devices(stage,device_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS echo_value_subject ON echo_value_devices(stage,subject_hash);
CREATE INDEX IF NOT EXISTS echo_value_active ON echo_value_usages(stage,device_id,active);
CREATE TABLE IF NOT EXISTS echo_value_revocations (
 stage TEXT NOT NULL, subject_hash TEXT NOT NULL, revoked_at INTEGER NOT NULL,
 PRIMARY KEY(stage,subject_hash)
);

CREATE TABLE IF NOT EXISTS echo_value_locks (
 stage TEXT PRIMARY KEY, owner TEXT NOT NULL, expires INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS echo_value_publish_cursor (
 stage TEXT PRIMARY KEY, device_id TEXT NOT NULL
);
