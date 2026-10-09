from pathlib import Path

import pytest
from fastapi.testclient import TestClient

INDEX = Path(__file__).resolve().parent.parent / "backend" / "frontend_dist" / "index.html"

pytestmark = pytest.mark.skipif(
    not INDEX.exists(),
    reason="frontend not built (run npm run build in frontend/)",
)


@pytest.fixture(scope="module")
def client():
    from backend.app import app

    return TestClient(app)


def test_root_serves_spa(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert '<div id="root">' in res.text


def test_spa_deep_link_falls_back_to_index(client):
    for path in ("/risk", "/weight", "/chat", "/some/unknown/route"):
        res = client.get(path)
        assert res.status_code == 200
        assert '<div id="root">' in res.text


def test_static_asset_served_directly(client):
    res = client.get("/manifest.webmanifest")
    assert res.status_code == 200
    assert res.text.lstrip().startswith("{")


def test_unknown_api_path_stays_json_404(client):
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/json")
    assert res.json()["detail"] == "Not found"


def test_known_api_routes_still_work(client):
    client.post(
        "/api/auth/register",
        json={"email": "spa@example.com", "password": "testpassword123"},
    )
    res = client.get("/api/weight/analytics")
    assert res.status_code == 200
    assert res.json()["entry_count"] >= 0
