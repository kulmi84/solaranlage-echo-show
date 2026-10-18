CREATE TABLE IF NOT EXISTS pv (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  power_w REAL NOT NULL CHECK (power_w >= 0),
  received_at TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}'
);

-- Additive migration. Existing pv rows are not changed.
CREATE TABLE IF NOT EXISTS solar_history (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  received_at TEXT NOT NULL,
  history_json TEXT NOT NULL
);
