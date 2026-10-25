"""A local SQLite journal for the lab's admitted actions."""
from contextlib import closing
from pathlib import Path
import sqlite3

from policy import Decision


class SQLiteLedger:
    def __init__(self, path, timeout=5):
        if str(path) == ":memory:":
            raise ValueError("Use a file path: this ledger opens one connection per operation")
        self.path = Path(path)
        self.timeout = timeout
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY,
                    key_id TEXT NOT NULL,
                    request_id TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    value TEXT NOT NULL,
                    admitted_at REAL NOT NULL,
                    replay_until REAL NOT NULL
                )
            """)
            connection.execute("CREATE INDEX IF NOT EXISTS replay_lookup ON actions (key_id, request_id, replay_until)")
            connection.execute("CREATE INDEX IF NOT EXISTS rate_lookup ON actions (key_id, admitted_at)")

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=self.timeout, isolation_level=None)
        try:
            connection.execute("PRAGMA synchronous=FULL")
        except BaseException:
            connection.close()
            raise
        return connection

    def admit(self, obj, key_id, clock, disabled):
        with closing(self.connect()) as connection:
            # Reserve the writer before reading replay/rate state. Two processes
            # must not both read "absent" and then insert the same action.
            connection.execute("BEGIN IMMEDIATE")
            try:
                now = clock()
                if "freshness" not in disabled and abs(now - obj["timestamp"]) > 30:
                    return Decision(403, "freshness")
                replay = connection.execute(
                    "SELECT 1 FROM actions WHERE key_id=? AND request_id=? AND replay_until>? LIMIT 1",
                    (key_id, obj["request_id"], now),
                ).fetchone()
                if "replay" not in disabled and replay:
                    return Decision(409, "replay")
                recent = connection.execute(
                    "SELECT COUNT(*) FROM actions WHERE key_id=? AND admitted_at>?",
                    (key_id, now - 2),
                ).fetchone()[0]
                if "rate" not in disabled and recent >= 3:
                    return Decision(429, "rate")
                # One row is both the recorded action and the replay/rate state.
                # There is no separate nonce write that can commit on its own.
                connection.execute(
                    "INSERT INTO actions (key_id,request_id,resource,value,admitted_at,replay_until) VALUES (?,?,?,?,?,?)",
                    (key_id, obj["request_id"], obj["resource"], obj["value"], now, now + 61),
                )
                connection.commit()
                return Decision(200, "accepted")
            finally:
                if connection.in_transaction:
                    connection.rollback()

    @property
    def effects(self):
        with closing(self.connect()) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT key_id, request_id, resource, value FROM actions ORDER BY id"
            ).fetchall()
        return [dict(row) for row in rows]
