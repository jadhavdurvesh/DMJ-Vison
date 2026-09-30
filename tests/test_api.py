from fastapi.testclient import TestClient

from vision_system.main import app

client = TestClient(app)


def test_health_and_dashboard_are_available():
    assert client.get("/api/health").json()["status"] == "ok"
    response = client.get("/")
    assert response.status_code == 200
    assert "OPERATIONS CONSOLE" in response.text


def test_overview_and_track_timeline():
    overview = client.get("/api/overview").json()
    assert overview["active_tracks"] >= 1
    tracks = client.get("/api/tracks?state=active").json()
    assert tracks and tracks[0]["state"] == "active"
    detail = client.get(f"/api/tracks/{tracks[0]['id']}", headers={"X-Operator": "test-user"})
    assert detail.status_code == 200
    assert len(detail.json()["observations"]) >= 1


def test_new_observation_creates_pseudonymous_track():
    response = client.post("/api/observations", json={"camera_id":"atrium","zone_id":"central-walkway","confidence":0.81,"quality":0.7})
    assert response.status_code == 201
    assert response.json()["id"].startswith("trk_")


def test_unknown_camera_is_rejected():
    response = client.post("/api/tracks/trk_any/observations", json={"camera_id":"unknown","zone_id":"x","confidence":0.8})
    assert response.status_code == 422


def test_continuity_mesh_returns_explainable_topology_candidate():
    response = client.get("/api/tracks/trk_7f2a/continuity-candidates", headers={"X-Operator": "test-user"})
    assert response.status_code == 200
    candidate = response.json()[0]
    assert candidate["track_id"] == "trk_ae10"
    assert candidate["tier"] in {"weak", "possible", "review"}
    assert "configured camera route" in candidate["evidence"]


def test_continuity_candidates_missing_track_is_not_found():
    assert client.get("/api/tracks/missing/continuity-candidates").status_code == 404
