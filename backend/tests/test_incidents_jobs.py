from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_incident_create_and_list(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    payload = {"id":"i1","tenant_id":"t1","description":"leak","status":"open"}
    r = client.post("/incident/create", json=payload)
    assert r.status_code == 200
    r2 = client.get("/incident/list/t1")
    assert r2.status_code == 200
    assert "incidents" in r2.json()


def test_job_create_and_list(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    payload = {"id":"j1","incident_id":"i1","contractor_id":"c1","status":"scheduled"}
    r = client.post("/job/create", json=payload)
    assert r.status_code == 200
    r2 = client.get("/job/list/c1")
    assert r2.status_code == 200
    assert "jobs" in r2.json()

