-- Additive preparation only. Apply before enabling /v2/enroll; no existing rows change.
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS enrollment_keys (
 key_hash TEXT PRIMARY KEY,
 tenant TEXT REFERENCES households(id) ON DELETE SET NULL,
 created INTEGER NOT NULL
);
-- A NULL tenant is a revocation tombstone: an erased setup cannot revive its old writer.
CREATE TABLE IF NOT EXISTS enrollment_limits (
 kind TEXT NOT NULL CHECK(kind IN ('hour','day')),
 subject TEXT NOT NULL,
 period_start INTEGER NOT NULL,
 registrations INTEGER NOT NULL,
 expires INTEGER NOT NULL,
 PRIMARY KEY(kind,subject,period_start)
);
