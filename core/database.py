"""SQLite persistence for Asaan Qanoon AI.

The database is intentionally dependency-free and can be moved to a hosted database
later without changing the Streamlit page contracts.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class Database:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def initialize(self):
        with self.connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT UNIQUE,
                    role TEXT NOT NULL DEFAULT 'Citizen',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    language TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY,
                    conversation_id INTEGER NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS cases (
                    id INTEGER PRIMARY KEY,
                    title TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'In progress',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY,
                    template_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
                now = self.now()
                conn.executemany(
                    "INSERT INTO users(name,email,role,created_at) VALUES(?,?,?,?)",
                    [
                        ("Demo Citizen", "citizen@example.com", "Citizen", now),
                        ("Workspace Admin", "admin@example.com", "Admin", now),
                    ],
                )

    @staticmethod
    def now():
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

    def create_case(self, title, intent):
        now = self.now()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO cases(title,intent,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                (title, intent, "In progress", now, now),
            )
            return cur.lastrowid

    def list_cases(self):
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(
                "SELECT * FROM cases ORDER BY updated_at DESC, id DESC"
            )]

    def update_case_status(self, case_id, status):
        with self.connect() as conn:
            conn.execute(
                "UPDATE cases SET status=?, updated_at=? WHERE id=?",
                (status, self.now(), case_id),
            )

    def save_interaction(self, title, language, question, answer):
        now = self.now()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO conversations(title,language,created_at) VALUES(?,?,?)",
                (title[:120], language, now),
            )
            conversation_id = cur.lastrowid
            conn.executemany(
                "INSERT INTO messages(conversation_id,role,content,created_at) VALUES(?,?,?,?)",
                [(conversation_id, "user", question, now), (conversation_id, "assistant", answer, now)],
            )
            return conversation_id

    def save_document(self, template_type, title, content):
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO documents(template_type,title,content,created_at) VALUES(?,?,?,?)",
                (template_type, title[:120], content, self.now()),
            )
            return cur.lastrowid

    def set_setting(self, key, value):
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO settings(key,value,updated_at) VALUES(?,?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                (key, str(value), self.now()),
            )

    def get_setting(self, key, default=None):
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            return row["value"] if row else default

    def dashboard_data(self):
        with self.connect() as conn:
            cases = [dict(row) for row in conn.execute(
                "SELECT id,title,intent,status,created_at,updated_at FROM cases ORDER BY updated_at DESC LIMIT 20"
            )]
            users = [dict(row) for row in conn.execute(
                "SELECT id,name,email,role,created_at FROM users ORDER BY id DESC LIMIT 20"
            )]
            return {
                "generated_at": self.now(),
                "metrics": {
                    "users": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                    "cases": conn.execute("SELECT COUNT(*) FROM cases WHERE status='In progress'").fetchone()[0],
                    "documents": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
                    "questions": conn.execute("SELECT COUNT(*) FROM messages WHERE role='user'").fetchone()[0],
                },
                "users": users,
                "cases": cases,
            }

    def export_dashboard_data(self, destination):
        output = Path(destination)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            "window.ASAAN_QANOON_DATA = " + json.dumps(self.dashboard_data()) + ";",
            encoding="utf-8",
        )
