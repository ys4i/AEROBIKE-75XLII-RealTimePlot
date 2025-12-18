PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS members (
  member_id     INTEGER PRIMARY KEY AUTOINCREMENT,
  subject_code  TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  session_id  INTEGER PRIMARY KEY AUTOINCREMENT,
  member_id   INTEGER NOT NULL,
  load_level  REAL NOT NULL,
  started_at  TEXT NOT NULL,
  ended_at    TEXT,
  memo        TEXT,
  FOREIGN KEY(member_id) REFERENCES members(member_id)
);

CREATE TABLE IF NOT EXISTS samples (
  session_id    INTEGER NOT NULL,
  t_ms          INTEGER NOT NULL,
  hr_bpm        REAL,
  cadence_rpm   REAL,
  raw_line      TEXT,
  PRIMARY KEY (session_id, t_ms),
  FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_samples_session_time
  ON samples(session_id, t_ms);
