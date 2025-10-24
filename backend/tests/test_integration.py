from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


def test_chat_send_and_history_dev_auth(monkeypatch):
    # Bypass auth
    monkeypatch.setenv("AUTH_DISABLED", "true")
    payload = {
        "user_id": "u1",
        "role": "tenant",
        "message": "hello",
        "timestamp": "2024-01-01T00:00:00Z",
        "thread_id": "t1",
        "client_id": "client-test",
    }
    r = client.post("/chat/send", json=payload)
    assert r.status_code == 200
    r2 = client.get("/chat/history/t1")
    assert r2.status_code == 200
    assert "messages" in r2.json()


def test_thread_create_and_list(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    payload = {
        "thread_id": "thread1",
        "title": "Support",
        "participants": ["u1", "u2"],
    }
    r = client.post("/thread/create", json=payload)
    assert r.status_code == 200
    r2 = client.get("/thread/list/u1")
    assert r2.status_code == 200
    data = r2.json()
    assert "threads" in data


def test_agent_summary(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")
    r = client.get("/agent/summarize_thread/default")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
