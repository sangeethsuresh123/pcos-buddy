"""SQLite-backed symptom tracking store and cycle analysis helpers."""

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from backend.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS symptom_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    entry_date TEXT NOT NULL,
    -- Menstrual cycle
    period_flow INTEGER,           -- 0=none, 1=spotting, 2=light, 3=medium, 4=heavy
    period_day INTEGER,            -- Day of cycle (1 = first day of period)
    cycle_length INTEGER,          -- Total cycle length if known
    -- Physical symptoms (0-10 scale)
    abdominal_pain INTEGER,
    breast_tenderness INTEGER,
    bloating INTEGER,
    headache INTEGER,
    fatigue INTEGER,
    acne INTEGER,
    hair_loss INTEGER,
    hirsutism INTEGER,
    skin_darkening INTEGER,
    -- Mood/mental (0-10 scale)
    mood_swings INTEGER,
    anxiety INTEGER,
    depression INTEGER,
    irritability INTEGER,
    -- Lifestyle
    exercise_minutes INTEGER,
    sleep_hours REAL,
    stress_level INTEGER,          -- 1-10
    diet_quality INTEGER,          -- 1-10
    -- Notes
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, entry_date)
);

CREATE TABLE IF NOT EXISTS cycle_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT,
    cycle_length INTEGER,
    flow_pattern TEXT,             -- JSON: daily flow ratings
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS symptom_profile (
    user_id INTEGER PRIMARY KEY,
    typical_cycle_length INTEGER,
    typical_period_length INTEGER,
    last_period_start TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


SYMPTOM_FIELDS = [
    "period_flow",
    "period_day",
    "cycle_length",
    "abdominal_pain",
    "breast_tenderness",
    "bloating",
    "headache",
    "fatigue",
    "acne",
    "hair_loss",
    "hirsutism",
    "skin_darkening",
    "mood_swings",
    "anxiety",
    "depression",
    "irritability",
    "exercise_minutes",
    "sleep_hours",
    "stress_level",
    "diet_quality",
]


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    except sqlite3.Error:
        return set()


def _migrate(conn: sqlite3.Connection) -> None:
    entry_cols = _table_columns(conn, "symptom_entries")
    legacy = bool(entry_cols) and "user_id" not in entry_cols
    if legacy:
        conn.executescript("ALTER TABLE symptom_entries RENAME TO symptom_entries_legacy;")

    event_cols = _table_columns(conn, "cycle_events")
    if event_cols and "user_id" not in event_cols:
        conn.execute("DROP TABLE cycle_events")

    profile_cols = _table_columns(conn, "symptom_profile")
    if profile_cols and "user_id" not in profile_cols:
        conn.execute("DROP TABLE symptom_profile")

    conn.executescript(SCHEMA)

    if legacy:
        cols = ", ".join(["id", "user_id", "entry_date"] + SYMPTOM_FIELDS + ["notes", "created_at"])
        sel_cols = ", ".join(["id", "0 as user_id", "entry_date"] + SYMPTOM_FIELDS + ["notes", "created_at"])
        conn.execute(f"INSERT INTO symptom_entries ({cols}) SELECT {sel_cols} FROM symptom_entries_legacy")
        conn.execute("DROP TABLE symptom_entries_legacy")


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.weight_db_path).parent / "symptoms.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    _migrate(conn)
    return conn


def get_profile(user_id: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT typical_cycle_length, typical_period_length, last_period_start "
            "FROM symptom_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def upsert_profile(user_id: int, data: dict) -> dict:
    with _connect() as conn:
        conn.execute(
            """INSERT INTO symptom_profile (user_id, typical_cycle_length, typical_period_length, last_period_start, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                   typical_cycle_length = excluded.typical_cycle_length,
                   typical_period_length = excluded.typical_period_length,
                   last_period_start = excluded.last_period_start,
                   updated_at = excluded.updated_at""",
            (
                user_id,
                data.get("typical_cycle_length"),
                data.get("typical_period_length"),
                data.get("last_period_start"),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        row = conn.execute(
            "SELECT typical_cycle_length, typical_period_length, last_period_start "
            "FROM symptom_profile WHERE user_id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else {}


def list_entries(user_id: int, days: int | None = None) -> list[dict]:
    query = (
        "SELECT id, entry_date, "
        + ", ".join(SYMPTOM_FIELDS)
        + ", notes FROM symptom_entries WHERE user_id = ?"
    )
    params: tuple = (user_id,)
    if days:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        query += " AND entry_date >= ?"
        params = (user_id, cutoff)
    query += " ORDER BY entry_date ASC"
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [_entry_dict(r) for r in rows]


def get_entry(user_id: int, entry_date: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, entry_date, "
            + ", ".join(SYMPTOM_FIELDS)
            + ", notes FROM symptom_entries WHERE user_id = ? AND entry_date = ?",
            (user_id, entry_date),
        ).fetchone()
    return _entry_dict(row) if row else None


def upsert_entry(user_id: int, entry: dict) -> dict:
    fields = ["entry_date"] + SYMPTOM_FIELDS + ["notes"]
    placeholders = ", ".join(["?"] * len(fields))
    updates = ", ".join([f"{f} = excluded.{f}" for f in fields if f != "entry_date"])

    with _connect() as conn:
        conn.execute(
            f"INSERT INTO symptom_entries (user_id, {', '.join(fields)}) "
            f"VALUES (?, {placeholders}) "
            f"ON CONFLICT(user_id, entry_date) DO UPDATE SET {updates}",
            (user_id,) + tuple(entry.get(f) for f in fields),
        )
        row = conn.execute(
            "SELECT id, entry_date, " + ", ".join(SYMPTOM_FIELDS) + ", notes "
            "FROM symptom_entries WHERE user_id = ? AND entry_date = ?",
            (user_id, entry["entry_date"]),
        ).fetchone()
    return _entry_dict(row)


def delete_entry(user_id: int, entry_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute(
            "DELETE FROM symptom_entries WHERE id = ? AND user_id = ?", (entry_id, user_id)
        )
    return cur.rowcount > 0


def _entry_dict(row: sqlite3.Row) -> dict:
    d = {"id": int(row["id"]), "entry_date": row["entry_date"], "notes": row["notes"]}
    for f in SYMPTOM_FIELDS:
        val = row[f]
        d[f] = int(val) if val is not None else None
    return d


def add_cycle_event(user_id: int, event: dict) -> dict:
    with _connect() as conn:
        cur = conn.execute(
            """INSERT INTO cycle_events (user_id, start_date, end_date, cycle_length, flow_pattern, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                event["start_date"],
                event.get("end_date"),
                event.get("cycle_length"),
                event.get("flow_pattern"),
                event.get("notes"),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        row = conn.execute(
            "SELECT id, start_date, end_date, cycle_length, flow_pattern, notes, created_at "
            "FROM cycle_events WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return _cycle_event_dict(row)


def list_cycle_events(user_id: int, limit: int = 20) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, start_date, end_date, cycle_length, flow_pattern, notes, created_at "
            "FROM cycle_events WHERE user_id = ? ORDER BY start_date DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [_cycle_event_dict(r) for r in rows]


def _cycle_event_dict(row: sqlite3.Row) -> dict:
    import json
    return {
        "id": int(row["id"]),
        "start_date": row["start_date"],
        "end_date": row["end_date"],
        "cycle_length": row["cycle_length"],
        "flow_pattern": json.loads(row["flow_pattern"]) if row["flow_pattern"] else None,
        "notes": row["notes"],
        "created_at": row["created_at"],
    }


def compute_cycle_analysis(user_id: int, entries: list[dict], profile: dict | None) -> dict:
    """Analyze cycle regularity, predict next period, identify symptom patterns."""
    if not entries:
        return {"cycles": [], "avg_cycle_length": None, "avg_period_length": None,
                "next_period_estimate": None, "phase": "unknown", "symptom_patterns": {}}

    period_days = [e for e in entries if (e.get("period_flow") or 0) > 0]
    if not period_days:
        return {"cycles": [], "avg_cycle_length": None, "avg_period_length": None,
                "next_period_estimate": None, "phase": "unknown", "symptom_patterns": {}}

    cycles = []
    period_starts = sorted({e["entry_date"] for e in period_days if e.get("period_day", 0) == 1})

    for i in range(len(period_starts) - 1):
        start = date.fromisoformat(period_starts[i])
        next_start = date.fromisoformat(period_starts[i + 1])
        length = (next_start - start).days
        if 15 <= length <= 60:
            cycles.append({"start": period_starts[i], "length": length})

    avg_cycle = round(sum(c["length"] for c in cycles) / len(cycles), 1) if cycles else None
    period_lengths = []
    for c in cycles:
        start = date.fromisoformat(c["start"])
        end = start + timedelta(days=c["length"])
        period_end = [e for e in period_days if start <= date.fromisoformat(e["entry_date"]) < end]
        if period_end:
            period_lengths.append(len(period_end))
    avg_period = round(sum(period_lengths) / len(period_lengths), 1) if period_lengths else None

    last_start = date.fromisoformat(period_starts[-1]) if period_starts else None
    next_est = None
    phase = "unknown"
    if last_start and avg_cycle:
        next_est = (last_start + timedelta(days=avg_cycle)).isoformat()
        days_since = (date.today() - last_start).days
        if days_since < 0:
            phase = "pre-period"
        elif days_since <= 5:
            phase = "menstrual"
        elif days_since <= 14:
            phase = "follicular"
        elif days_since <= avg_cycle - 1:
            phase = "luteal"
        else:
            phase = "late-luteal"

    symptom_patterns = _analyze_symptom_patterns(entries, period_starts, avg_cycle or 28)

    return {
        "cycles": cycles,
        "avg_cycle_length": avg_cycle,
        "avg_period_length": avg_period,
        "next_period_estimate": next_est,
        "phase": phase,
        "days_since_last_period": (date.today() - last_start).days if last_start else None,
        "symptom_patterns": symptom_patterns,
    }


def _analyze_symptom_patterns(entries: list[dict], period_starts: list[str], avg_cycle: int) -> dict:
    if len(period_starts) < 2:
        return {}

    phase_symptoms = {"menstrual": [], "follicular": [], "luteal": []}
    for e in entries:
        if not e.get("period_day"):
            continue
        d = e["period_day"]
        if 1 <= d <= 5:
            phase = "menstrual"
        elif d <= 14:
            phase = "follicular"
        else:
            phase = "luteal"

        for symptom in ["abdominal_pain", "breast_tenderness", "bloating", "fatigue",
                        "mood_swings", "anxiety", "acne", "headache"]:
            val = e.get(symptom)
            if val and val >= 4:
                phase_symptoms[phase].append(symptom)

    patterns = {}
    for phase, symptoms in phase_symptoms.items():
        if symptoms:
            from collections import Counter
            counts = Counter(symptoms)
            patterns[phase] = [{"symptom": s, "frequency": c} for s, c in counts.most_common(5)]

    return patterns


def get_latest_symptoms_for_ml(user_id: int) -> dict:
    """Extract latest symptom values mapped to ML feature names."""
    entries = list_entries(user_id, days=30)
    if not entries:
        return {}

    latest = entries[-1]
    mapping = {
        "Weight gain(Y/N)": 1 if (latest.get("bloating") or 0) >= 5 else 0,
        "hair growth(Y/N)": 1 if (latest.get("hirsutism") or 0) >= 4 else 0,
        "Skin darkening (Y/N)": 1 if (latest.get("skin_darkening") or 0) >= 4 else 0,
        "Hair loss(Y/N)": 1 if (latest.get("hair_loss") or 0) >= 4 else 0,
        "Reg.Exercise(Y/N)": 1 if (latest.get("exercise_minutes") or 0) >= 150 else 0,
        "Cycle(R/I)": 2 if _is_irregular(entries) else 1,
    }
    return mapping


def _is_irregular(entries: list[dict]) -> bool:
    period_starts = sorted({e["entry_date"] for e in entries if (e.get("period_flow") or 0) > 0 and e.get("period_day") == 1})
    if len(period_starts) < 3:
        return False
    lengths = []
    for i in range(len(period_starts) - 1):
        d1 = date.fromisoformat(period_starts[i])
        d2 = date.fromisoformat(period_starts[i + 1])
        lengths.append((d2 - d1).days)
    if not lengths:
        return False
    avg = sum(lengths) / len(lengths)
    return any(abs(l - avg) > 7 for l in lengths)