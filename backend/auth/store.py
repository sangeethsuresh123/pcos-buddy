"""SQLite-backed user accounts and opaque session tokens.

Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib, no extra deps).
Sessions are opaque random tokens; only their SHA-256 hash is stored so a DB
leak does not expose usable tokens.
"""

import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    google_id TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
"""


class EmailAlreadyRegistered(Exception):
    pass


def _migrate(conn: sqlite3.Connection) -> None:
    """Bring pre-existing databases up to date.

    Runs after SCHEMA; the google_id index must be created here (not in SCHEMA)
    so it works on databases whose users table predates the google_id column.
    """
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if columns and "google_id" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_google "
        "ON users(google_id) WHERE google_id IS NOT NULL"
    )


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.auth_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _public_user(row: sqlite3.Row) -> dict:
    return {
        "id": int(row["id"]),
        "email": row["email"],
        "created_at": row["created_at"],
    }


# --- password hashing ---


def hash_password(password: str) -> str:
    iterations = settings.auth_pbkdf2_iterations
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


# --- users ---


def create_user(email: str, password: str) -> dict:
    email = email.strip().lower()
    with _connect() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, hash_password(password)),
            )
        except sqlite3.IntegrityError as exc:
            raise EmailAlreadyRegistered(email) from exc
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return _public_user(row)


def authenticate(email: str, password: str) -> dict | None:
    email = email.strip().lower()
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if row is None or not verify_password(password, row["password_hash"]):
        return None
    return _public_user(row)


def get_user(user_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _public_user(row) if row else None


def get_or_create_google_user(email: str, google_id: str) -> dict:
    """Return the user linked to a Google account, linking by email when
    possible. Google users have no password (empty hash) so password login
    always fails for them."""
    email = email.strip().lower()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE google_id = ?", (google_id,)
        ).fetchone()
        if row:
            return _public_user(row)

        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if row:
            conn.execute(
                "UPDATE users SET google_id = ? WHERE id = ?", (google_id, row["id"])
            )
            return _public_user(row)

        cur = conn.execute(
            "INSERT INTO users (email, password_hash, google_id) VALUES (?, '', ?)",
            (email, google_id),
        )
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return _public_user(row)


# --- sessions ---


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (_now() + timedelta(days=settings.session_ttl_days)).isoformat()
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (_now().isoformat(),))
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
            (_hash_token(token), user_id, expires_at),
        )
    return token


def get_user_by_token(token: str) -> dict | None:
    if not token:
        return None
    with _connect() as conn:
        row = conn.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ? AND s.expires_at > ?",
            (_hash_token(token), _now().isoformat()),
        ).fetchone()
    return _public_user(row) if row else None


def delete_session(token: str) -> None:
    if not token:
        return
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))
