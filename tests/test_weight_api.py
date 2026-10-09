from datetime import date, timedelta

import pytest

from backend.config import settings
from backend.weight import store

from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "weight_db_path", str(tmp_path / "weight.db"))


@pytest.fixture()
def client():
    from backend.app import app

    return TestClient(app)


def _entry(day: str, weight: float, waist: float | None = None, hip: float | None = None):
    return {
        "id": 0,
        "entry_date": day,
        "weight_kg": weight,
        "waist_cm": waist,
        "hip_cm": hip,
        "notes": None,
    }


def test_profile_roundtrip(client):
    assert client.get("/api/weight/profile").json() == {"height_cm": None}

    resp = client.put("/api/weight/profile", json={"height_cm": 165})
    assert resp.status_code == 200
    assert resp.json() == {"height_cm": 165}
    assert client.get("/api/weight/profile").json() == {"height_cm": 165}


def test_profile_rejects_impossible_height(client):
    resp = client.put("/api/weight/profile", json={"height_cm": 50})
    assert resp.status_code == 422
    assert "height_cm must be >= 120" in resp.json()["detail"]


def test_entry_crud_and_upsert(client):
    payload = {
        "date": "2026-01-10",
        "weight_kg": 70.5,
        "waist_cm": 88,
        "hip_cm": 100,
        "notes": "morning",
    }
    resp = client.post("/api/weight/entries", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == "2026-01-10"
    assert body["weight_kg"] == 70.5
    entry_id = body["id"]

    # same day again -> upsert, not duplicate
    resp = client.post("/api/weight/entries", json={**payload, "weight_kg": 71.0})
    assert resp.status_code == 200
    assert resp.json()["id"] == entry_id
    assert resp.json()["weight_kg"] == 71.0

    entries = client.get("/api/weight/entries").json()
    assert len(entries) == 1

    assert client.delete(f"/api/weight/entries/{entry_id}").json() == {"deleted": True}
    assert client.get("/api/weight/entries").json() == []
    assert client.delete(f"/api/weight/entries/{entry_id}").status_code == 404


def test_entry_rejects_future_date(client):
    future = date.today().replace(year=date.today().year + 1).isoformat()
    resp = client.post("/api/weight/entries", json={"date": future, "weight_kg": 70})
    assert resp.status_code == 422
    assert "cannot be in the future" in resp.json()["detail"]


def test_entry_rejects_out_of_range_weight(client):
    resp = client.post("/api/weight/entries", json={"date": "2026-01-10", "weight_kg": 10})
    assert resp.status_code == 422
    assert "weight_kg must be >= 25" in resp.json()["detail"]


def test_analytics_endpoint(client):
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    client.put("/api/weight/profile", json={"height_cm": 165})
    client.post("/api/weight/entries", json={"date": week_ago, "weight_kg": 78})
    client.post("/api/weight/entries", json={"date": date.today().isoformat(), "weight_kg": 80.5})

    data = client.get("/api/weight/analytics").json()
    assert data["entry_count"] == 2
    assert data["height_cm"] == 165
    assert data["bmi"] == 29.6
    assert data["bmi_category"] == "obese"
    assert data["latest"]["weight_kg"] == 80.5
    assert len(data["series"]) == 2
    assert any(f["type"] == "rapid_gain" for f in data["flags"])


def test_analytics_empty_state(client):
    data = client.get("/api/weight/analytics").json()
    assert data["entry_count"] == 0
    assert data["bmi"] is None
    assert data["milestones"] is None
    assert data["flags"] == []
    assert data["series"] == []


def test_bmi_category_cutoffs():
    assert store.bmi_category(17.9) == "underweight"
    assert store.bmi_category(22.9) == "normal"
    assert store.bmi_category(23.0) == "overweight"
    assert store.bmi_category(25.0) == "obese"


def test_analytics_gain_flags_and_ratios():
    entries = [
        _entry("2026-01-20", 77.9, waist=95, hip=105),
        _entry("2026-01-31", 80.5, waist=96, hip=106),
    ]
    data = store.compute_analytics(entries, height_cm=165, today=date(2026, 1, 31))

    assert data["bmi"] == 29.6
    assert data["waist_height_ratio"] == 0.58
    assert data["waist_hip_ratio"] == 0.906
    assert data["delta_30d_kg"] == 2.6
    assert data["pace_kg_per_week"] == 0.65
    assert data["trend_direction"] == "stable"
    types = [f["type"] for f in data["flags"]]
    assert "rapid_gain" in types
    assert data["milestones"]["five_percent"]["progress"] == 0.0


def test_analytics_milestones_and_decreasing_trend():
    entries = [
        _entry("2025-11-01", 80.0),
        _entry("2025-12-01", 76.0),
        _entry("2026-01-01", 74.0),
        _entry("2026-01-25", 72.0),
        _entry("2026-01-31", 71.8),
    ]
    data = store.compute_analytics(entries, height_cm=170, today=date(2026, 1, 31))

    assert data["trend_direction"] == "decreasing"
    assert data["trend_slope_kg_per_month"] < -0.5
    assert data["milestones"]["five_percent"]["achieved"] is True
    assert data["milestones"]["ten_percent"]["achieved"] is True
    assert data["milestones"]["ten_percent"]["loss_required_kg"] == 8.0
    assert data["delta_30d_kg"] == -2.2
    milestone_flags = [f for f in data["flags"] if f["type"] == "milestone_reached"]
    assert len(milestone_flags) == 2
    assert all(f["severity"] == "positive" for f in milestone_flags)


def test_analytics_plateau_flag():
    entries = [
        _entry("2026-01-19", 75.0),
        _entry("2026-01-26", 75.2),
        _entry("2026-02-02", 74.9),
        _entry("2026-02-09", 75.1),
    ]
    data = store.compute_analytics(entries, height_cm=160, today=date(2026, 2, 14))
    types = [f["type"] for f in data["flags"]]
    assert "plateau" in types
    assert data["trend_direction"] == "stable"


def test_analytics_stale_log_flag():
    entries = [_entry("2026-01-19", 75.0)]
    data = store.compute_analytics(entries, height_cm=160, today=date(2026, 2, 15))
    types = [f["type"] for f in data["flags"]]
    assert "stale_log" in types


def test_analytics_without_height(client):
    client.post("/api/weight/entries", json={"date": "2026-01-10", "weight_kg": 70})
    data = client.get("/api/weight/analytics").json()
    assert data["bmi"] is None
    assert data["bmi_category"] is None
    assert data["waist_height_ratio"] is None
    assert data["series"][0]["bmi"] is None
