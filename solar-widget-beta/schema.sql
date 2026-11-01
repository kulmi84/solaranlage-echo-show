CREATE TABLE IF NOT EXISTS beta_snapshot (
  id INTEGER PRIMARY KEY CHECK(id = 1),
  payload TEXT NOT NULL,
  received_at TEXT NOT NULL
);
