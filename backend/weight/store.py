"""SQLite-backed weight tracking store and pure analytics helpers."""

import math
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

from backend.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS weight_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT NOT NULL UNIQUE,
    weight_kg REAL NOT NULL,
    waist_cm REAL,
    hip_cm REAL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS weight_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    height_cm REAL NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.weight_db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def get_profile_height() -> float | None:
    with _connect() as conn:
        row = conn.execute("SELECT height_cm FROM weight_profile WHERE id = 1").fetchone()
    return float(row["height_cm"]) if row else None


def set_profile_height(height_cm: float) -> float:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO weight_profile (id, height_cm, updated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET height_cm = excluded.height_cm, "
            "updated_at = excluded.updated_at",
            (height_cm, datetime.now().isoformat(timespec="seconds")),
        )
    return height_cm


def list_entries(days: int | None = None) -> list[dict]:
    query = "SELECT id, entry_date, weight_kg, waist_cm, hip_cm, notes FROM weight_entries"
    params: tuple = ()
    if days:
        cutoff = (date.today() - timedelta(days=days)).isoformat()
        query += " WHERE entry_date >= ?"
        params = (cutoff,)
    query += " ORDER BY entry_date ASC"
    with _connect() as conn:
        rows = conn.execute(query, params).fetchall()
    return [
        {
            "id": int(r["id"]),
            "entry_date": r["entry_date"],
            "weight_kg": float(r["weight_kg"]),
            "waist_cm": float(r["waist_cm"]) if r["waist_cm"] is not None else None,
            "hip_cm": float(r["hip_cm"]) if r["hip_cm"] is not None else None,
            "notes": r["notes"],
        }
        for r in rows
    ]


def upsert_entry(entry: dict) -> dict:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO weight_entries (entry_date, weight_kg, waist_cm, hip_cm, notes) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(entry_date) DO UPDATE SET weight_kg = excluded.weight_kg, "
            "waist_cm = excluded.waist_cm, hip_cm = excluded.hip_cm, notes = excluded.notes",
            (
                entry["entry_date"],
                entry["weight_kg"],
                entry.get("waist_cm"),
                entry.get("hip_cm"),
                entry.get("notes"),
            ),
        )
        row = conn.execute(
            "SELECT id, entry_date, weight_kg, waist_cm, hip_cm, notes "
            "FROM weight_entries WHERE entry_date = ?",
            (entry["entry_date"],),
        ).fetchone()
    return _entry_dict(row)


def delete_entry(entry_id: int) -> bool:
    with _connect() as conn:
        cur = conn.execute("DELETE FROM weight_entries WHERE id = ?", (entry_id,))
    return cur.rowcount > 0


def _entry_dict(row: sqlite3.Row) -> dict:
    return {
        "id": int(row["id"]),
        "entry_date": row["entry_date"],
        "weight_kg": float(row["weight_kg"]),
        "waist_cm": float(row["waist_cm"]) if row["waist_cm"] is not None else None,
        "hip_cm": float(row["hip_cm"]) if row["hip_cm"] is not None else None,
        "notes": row["notes"],
    }


def bmi_category(bmi: float) -> str:
    """WHO Asia-Pacific / Asian-Indian cutoffs (overweight >=23, obese >=25)."""
    if bmi < 18.5:
        return "underweight"
    if bmi < 23:
        return "normal"
    if bmi < 25:
        return "overweight"
    return "obese"


def _parse(d: str) -> date:
    return date.fromisoformat(d)


def _value_nearest_days_ago(entries: list[dict], days: int, today: date) -> float | None:
    """Weight closest to `days` before today (prefers the entry on or before that day)."""
    if not entries:
        return None
    target = today - timedelta(days=days)
    on_or_before = [e for e in entries if _parse(e["entry_date"]) <= target]
    pool = on_or_before or entries
    best = min(pool, key=lambda e: abs((_parse(e["entry_date"]) - target).days))
    return best["weight_kg"]


def _slope_per_day(points: list[tuple[float, float]]) -> float:
    n = len(points)
    mean_x = sum(p[0] for p in points) / n
    mean_y = sum(p[1] for p in points) / n
    denom = sum((p[0] - mean_x) ** 2 for p in points)
    if denom == 0:
        return 0.0
    return sum((x - mean_x) * (y - mean_y) for x, y in points) / denom


def compute_analytics(entries: list[dict], height_cm: float | None,
                      today: date | None = None) -> dict:
    today = today or date.today()
    latest = entries[-1] if entries else None

    bmi = None
    category = None
    if latest and height_cm:
        bmi = round(latest["weight_kg"] / ((height_cm / 100) ** 2), 1)
        category = bmi_category(bmi)

    whtr = None
    whr = None
    if latest and latest["waist_cm"] and height_cm:
        whtr = round(latest["waist_cm"] / height_cm, 2)
    if latest and latest["waist_cm"] and latest["hip_cm"]:
        whr = round(latest["waist_cm"] / latest["hip_cm"], 3)

    delta_30 = delta_90 = None
    if latest:
        ref30 = _value_nearest_days_ago(entries, 30, today)
        ref90 = _value_nearest_days_ago(entries, 90, today)
        if ref30 is not None and ref30 != latest["weight_kg"]:
            delta_30 = round(latest["weight_kg"] - ref30, 2)
        if ref90 is not None and ref90 != latest["weight_kg"]:
            delta_90 = round(latest["weight_kg"] - ref90, 2)

    slope_month = None
    direction = "stable"
    window = [e for e in entries if (_parse(e["entry_date"]) >= today - timedelta(days=90))]
    if len(window) >= 3:
        base = _parse(window[0]["entry_date"])
        points = [((_parse(e["entry_date"]) - base).days, e["weight_kg"]) for e in window]
        slope_month = round(_slope_per_day(points) * 30, 2)
        if slope_month > 0.5:
            direction = "increasing"
        elif slope_month < -0.5:
            direction = "decreasing"

    pace_weekly = None
    if latest:
        ref28 = _value_nearest_days_ago(entries, 28, today)
        if ref28 is not None and ref28 != latest["weight_kg"]:
            pace_weekly = round((latest["weight_kg"] - ref28) / 4, 2)

    milestones = None
    flags: list[dict] = []
    if latest:
        baseline_weight = entries[0]["weight_kg"]
        lost = baseline_weight - latest["weight_kg"]
        milestones = {}
        for label, pct in (("five_percent", 0.05), ("ten_percent", 0.10)):
            target_weight = baseline_weight * (1 - pct)
            progress = 0.0 if baseline_weight <= latest["weight_kg"] else \
                min(1.0, lost / (baseline_weight * pct))
            milestones[label] = {
                "target_weight_kg": round(target_weight, 1),
                "loss_required_kg": round(baseline_weight * pct, 1),
                "progress": round(progress, 2),
                "achieved": progress >= 1.0,
            }
            if progress >= 1.0:
                flags.append({
                    "type": "milestone_reached",
                    "severity": "positive",
                    "message": f"You've reached your {int(pct * 100)}% weight-loss milestone "
                               f"({round(baseline_weight * pct, 1)} kg). Well done!",
                })

        ref7 = _value_nearest_days_ago(entries, 7, today)
        if ref7 is not None:
            change = latest["weight_kg"] - ref7
            if change >= 2:
                flags.append({
                    "type": "rapid_gain",
                    "severity": "warning",
                    "message": f"Weight is up {round(change, 1)} kg within the last week. "
                               "Quick changes are often fluid retention — mention it at your next check-up.",
                })
            elif change <= -2:
                flags.append({
                    "type": "rapid_loss",
                    "severity": "warning",
                    "message": f"Weight is down {round(abs(change), 1)} kg within the last week — "
                               "faster than the recommended 0.5-1 kg/week. Speak with your provider.",
                })

        recent = [e for e in entries if _parse(e["entry_date"]) >= today - timedelta(days=28)]
        ref28 = _value_nearest_days_ago(entries, 28, today)
        if len(recent) >= 4 and ref28 is not None and abs(latest["weight_kg"] - ref28) < 0.5:
            flags.append({
                "type": "plateau",
                "severity": "info",
                "message": "Weight has been steady for 4 weeks. Plateaus are normal — "
                           "focus on strength training and sleep, and reassess in a month.",
            })

        if (today - _parse(latest["entry_date"])).days >= 14:
            flags.append({
                "type": "stale_log",
                "severity": "info",
                "message": "It's been over two weeks since your last log. Regular weigh-ins "
                           "make trends more reliable.",
            })

    series = [
        {
            "date": e["entry_date"],
            "weight_kg": e["weight_kg"],
            "bmi": round(e["weight_kg"] / ((height_cm / 100) ** 2), 1) if height_cm else None,
        }
        for e in entries
    ]

    return {
        "entry_count": len(entries),
        "latest": latest,
        "baseline": entries[0] if entries else None,
        "height_cm": height_cm,
        "bmi": bmi,
        "bmi_category": category,
        "waist_height_ratio": whtr,
        "waist_hip_ratio": whr,
        "delta_30d_kg": delta_30,
        "delta_90d_kg": delta_90,
        "trend_slope_kg_per_month": slope_month,
        "trend_direction": direction,
        "pace_kg_per_week": pace_weekly,
        "milestones": milestones,
        "flags": flags,
        "series": series,
    }
