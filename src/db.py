import sqlite3
from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AerobikeDB:
    def __init__(self, db_path: str = "aerodb.sqlite"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON;")
        self.conn.execute("PRAGMA journal_mode = WAL;")
        self.conn.execute("PRAGMA synchronous = NORMAL;")

    def init_schema(self, schema_path: str = "schema.sql") -> None:
        with open(schema_path, "r", encoding="utf-8") as f:
            self.conn.executescript(f.read())
        self.conn.commit()

    def get_or_create_member(self, subject_code: str) -> int:
        self.conn.execute(
            "INSERT OR IGNORE INTO members(subject_code) VALUES(?)",
            (subject_code,),
        )
        cur = self.conn.execute(
            "SELECT member_id FROM members WHERE subject_code=?",
            (subject_code,),
        )
        row = cur.fetchone()
        if row is None:
            raise RuntimeError("Failed to get or create member.")
        return row[0]

    def start_session(self, member_id: int, load_level: float, memo: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO sessions(member_id, load_level, started_at, memo) VALUES(?,?,?,?)",
            (member_id, load_level, now_iso(), memo),
        )
        self.conn.commit()
        return cur.lastrowid

    def end_session(self, session_id: int) -> None:
        self.conn.execute(
            "UPDATE sessions SET ended_at=? WHERE session_id=?",
            (now_iso(), session_id),
        )
        self.conn.commit()

    def insert_sample(
        self,
        session_id: int,
        t_ms: int,
        hr_bpm=None,
        cadence_rpm=None,
        raw_line=None,
    ) -> None:
        self.conn.execute(
            """INSERT OR REPLACE INTO samples(session_id, t_ms, hr_bpm, cadence_rpm, raw_line)
               VALUES(?,?,?,?,?)""",
            (session_id, t_ms, hr_bpm, cadence_rpm, raw_line),
        )

    def commit(self) -> None:
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
