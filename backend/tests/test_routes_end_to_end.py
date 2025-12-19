import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def disable_auth(monkeypatch):
    monkeypatch.setenv("AUTH_DISABLED", "true")


@pytest.fixture
def in_memory_state():
    return {
        "messages": [],
        "threads": [],
        "incidents": [],
        "jobs": [],
        "tasks": [],
        "contractors": {},
        "bids": [],
        "schedules": {},
    }


@pytest.fixture
def client(monkeypatch, in_memory_state):
    class FakePusher:
        def trigger(self, channel, event, payload):
            return {"channel": channel, "event": event, "payload": payload}

    class FakeChatRepo:
        def __init__(self):
            self.messages = in_memory_state["messages"]

        def put_message(self, payload):
            self.messages.append(payload)

        def list_messages(self, thread_id):
            return [m for m in self.messages if m.get("thread_id") == thread_id]

    class FakeThreadRepo:
        def __init__(self):
            self.threads = in_memory_state["threads"]

        def create_thread(self, payload):
            self.threads.append(payload)
            return payload

        def list_threads_for_user(self, user_id):
            return [t for t in self.threads if user_id in t.get("participants", [])]

    class FakeIncidentRepo:
        def __init__(self):
            self.incidents = in_memory_state["incidents"]

        def log_incident(self, payload):
            self.incidents.append(payload)

        def list_incidents(self, tenant_id):
            return [i for i in self.incidents if i.get("tenant_id") == tenant_id]

    class FakeJobRepo:
        def __init__(self):
            self.jobs = in_memory_state["jobs"]

        def create_job(self, payload):
            self.jobs.append(payload)

        def list_jobs(self, contractor_id):
            return [j for j in self.jobs if j.get("contractor_id") == contractor_id]

    class FakeTaskRepo:
        def __init__(self):
            self.tasks = in_memory_state["tasks"]

        def create_task(self, payload):
            self.tasks.append(payload)
            return payload

        def list_tasks(self, persona):
            return [t for t in self.tasks if t.get("persona") == persona or t.get("assigned_to") == persona]

        def update_status(self, task_id, status):
            for task in self.tasks:
                if task.get("task_id") == task_id:
                    task["status"] = status
                    break

    class FakeContractorRepo:
        def __init__(self):
            self.profiles = in_memory_state["contractors"]

        def upsert_profile(self, profile):
            self.profiles[profile["contractor_id"]] = profile

        def get_profile(self, contractor_id):
            return self.profiles.get(contractor_id)

        def list_by_skill(self, skill):
            return [p for p in self.profiles.values() if skill in p.get("skills", [])]

        def list_all(self):
            return list(self.profiles.values())

    class FakeJobBidRepo:
        def __init__(self):
            self.bids = in_memory_state["bids"]

        def list_for_contractor(self, contractor_id):
            return [b for b in self.bids if b.get("contractor_id") == contractor_id]

    class FakeScheduleRepo:
        def __init__(self):
            self.schedules = in_memory_state["schedules"]

        def add_entry(self, entity_id, schedule_id, entry):
            self.schedules.setdefault(entity_id, []).append({"schedule_id": schedule_id, **entry})

        def list_entries(self, entity_id):
            return self.schedules.get(entity_id, [])

    class FakeStripeService:
        def create_express_account(self, email, contractor_id, name=None):
            return {"account_id": f"acct_{contractor_id}", "status": "created", "email": email, "name": name}

        def add_external_bank_account(self, account_id, account_number, routing_number, account_holder_name, account_holder_type):
            return {
                "last4": account_number[-4:],
                "status": "verified",
                "bank_name": "Test Bank",
                "account_id": account_id,
            }

        def create_transfer(self, destination_account, amount_cents, description, metadata):
            return {"transfer_id": f"tr_{destination_account}", "amount": amount_cents, "description": description, "metadata": metadata}

    monkeypatch.setattr("app.routes.chat._get_pusher", lambda: FakePusher())
    monkeypatch.setattr("app.routes.chat.ChatRepo", FakeChatRepo)
    monkeypatch.setattr("app.routes.agent_summary.ChatRepo", FakeChatRepo)
    monkeypatch.setattr("app.routes.thread.ThreadRepo", FakeThreadRepo)
    monkeypatch.setattr("app.routes.incident.IncidentRepo", FakeIncidentRepo)
    monkeypatch.setattr("app.routes.job.JobRepo", FakeJobRepo)
    monkeypatch.setattr("app.routes.task.TaskRepo", FakeTaskRepo)
    monkeypatch.setattr("app.routes.contractor.ContractorRepo", FakeContractorRepo)
    monkeypatch.setattr("app.routes.contractor.JobBidRepo", FakeJobBidRepo)
    monkeypatch.setattr("app.routes.contractor.ScheduleRepo", FakeScheduleRepo)
    monkeypatch.setattr("app.routes.contractor.StripeService", FakeStripeService)

    return TestClient(app)


def test_chat_thread_and_summary_flow(client):
    chat_payload = {
        "user_id": "tenant-1",
        "role": "tenant",
        "message": "Hello!",
        "thread_id": "thread-123",
        "client_id": "web",
    }
    send_resp = client.post("/chat/send", json=chat_payload)
    assert send_resp.status_code == 200

    history_resp = client.get("/chat/history/thread-123")
    history = history_resp.json()["messages"]
    assert any(msg["message"] == "Hello!" for msg in history)

    summary_resp = client.get("/agent/summarize_thread/thread-123")
    assert "summary" in summary_resp.json()
    assert "Hello" in summary_resp.json()["summary"]

    thread_payload = {"thread_id": "thread-123", "title": "Support", "participants": ["tenant-1", "agent"]}
    create_thread_resp = client.post("/thread/create", json=thread_payload)
    assert create_thread_resp.status_code == 200

    list_threads = client.get("/thread/list/tenant-1").json()["threads"]
    assert any(t["thread_id"] == "thread-123" for t in list_threads)


def test_property_incident_job_and_task_endpoints(client):
    property_payload = {"name": "Unit 1", "address": "123 Main", "landlord_id": "landlord-1", "tenants": ["tenant-1"]}
    created_property = client.post("/property/create", json=property_payload).json()["property"]
    property_id = created_property["id"]

    landlord_properties = client.get(f"/property/list/{created_property['landlord_id']}").json()["properties"]
    assert any(p["id"] == property_id for p in landlord_properties)

    tenant_property = client.get(f"/property/tenant/tenant-1").json()["property"]
    assert tenant_property["id"] == property_id

    updated_property = client.put(f"/property/update/{property_id}", json={"name": "Unit 1B", "address": "123 Main", "landlord_id": "landlord-1", "tenants": ["tenant-1"]}).json()["property"]
    assert updated_property["name"] == "Unit 1B"

    add_tenant_resp = client.post("/property/add_tenant", params={"property_id": property_id, "tenant_id": "tenant-2"}).json()
    assert add_tenant_resp["status"] == "added"

    incident_payload = {"id": "inc-1", "tenant_id": "tenant-1", "description": "Leak", "status": "open"}
    inc_resp = client.post("/incident/create", json=incident_payload)
    assert inc_resp.status_code == 200

    incidents = client.get("/incident/list/tenant-1").json()["incidents"]
    assert any(i["id"] == "inc-1" for i in incidents)

    job_payload = {"id": "job-1", "incident_id": "inc-1", "contractor_id": "contractor-1", "status": "scheduled"}
    client.post("/job/create", json=job_payload)

    jobs = client.get("/job/list/contractor-1").json()["jobs"]
    assert any(j["id"] == "job-1" for j in jobs)

    task_payload = {
        "task_id": "task-1",
        "title": "Call tenant",
        "description": "Follow up",
        "persona": "landlord",
        "created_by": "landlord-1",
        "assigned_to": "property-manager",
    }
    created_task = client.post("/task/create", json=task_payload).json()["task"]
    assert created_task["task_id"] == "task-1"

    landlord_tasks = client.get("/task/list/landlord").json()["tasks"]
    assert any(t["task_id"] == "task-1" for t in landlord_tasks)

    update_resp = client.post("/task/update_status", json={"task_id": "task-1", "status": "done"})
    assert update_resp.status_code == 200

    updated_tasks = client.get("/task/list/property-manager").json()["tasks"]
    assert any(t["status"] == "done" for t in updated_tasks)


def test_contractor_profile_payment_and_availability(client):
    profile_payload = {"contractor_id": "contractor-1", "name": "Pat", "email": "pat@example.com", "skills": ["plumbing"]}
    profile_resp = client.post("/contractor/profile", json=profile_payload)
    assert profile_resp.status_code == 200

    bank_payload = {
        "contractor_id": "contractor-1",
        "account_number": "000123456789",
        "routing_number": "110000000",
        "account_holder_name": "Pat Contractor",
    }
    bank_resp = client.post("/contractor/bank-account", json=bank_payload)
    assert bank_resp.status_code == 200
    assert bank_resp.json()["payment_enabled"] is True

    payment_info = client.get("/contractor/payment-info/contractor-1").json()
    assert payment_info["has_stripe_account"] is True

    availability_payload = {"contractor_id": "contractor-1", "start": "2024-01-01T10:00:00Z", "end": "2024-01-01T12:00:00Z"}
    avail_resp = client.post("/contractor/availability", json=availability_payload)
    assert avail_resp.status_code == 200

    availability = client.get("/contractor/availability/contractor-1").json()["availability"]
    assert len(availability) == 1

    bids = client.get("/contractor/bids/contractor-1").json()["bids"]
    assert bids == []
