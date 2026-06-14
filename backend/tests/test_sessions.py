"""Session API tests (no real model calls — verifies create/list/get/abort)."""


def _setup(client):
    tool = client.post("/api/tools", json={
        "name": "greet",
        "description": "",
        "tags": [],
        "version": {
            "display_name": "greet",
            "model_facing_description": "Greet the user",
            "parameter_schema": {"type": "object", "properties": {}},
            "response_mode": "static",
            "static_response": {"greeting": "hello"},
        },
    }).json()
    mc = client.post("/api/model-configs", json={
        "name": "m",
        "base_url": "https://api.openai.com/v1",
        "model_snapshot": "gpt-4o-mini",
        "api_key_env": "TEST_KEY",
    }).json()
    plan = client.post("/api/plans", json={
        "name": "p",
        "description": "",
        "version": {
            "model_config_id": mc["id"],
            "tool_version_ids": [tool["versions"][0]["id"]],
            "system_prompt": "",
            "user_prompt": "Hello",
        },
    }).json()
    pv_id = plan["versions"][0]["id"]
    return pv_id


def test_create_session(client):
    pv_id = _setup(client)
    r = client.post("/api/sessions", json={"plan_version_id": pv_id})
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["plan_version_id"] == pv_id


def test_create_session_bad_plan_version(client):
    r = client.post("/api/sessions", json={"plan_version_id": "nonexistent"})
    assert r.status_code == 400


def test_list_sessions(client):
    pv_id = _setup(client)
    client.post("/api/sessions", json={"plan_version_id": pv_id})
    client.post("/api/sessions", json={"plan_version_id": pv_id})
    r = client.get("/api/sessions")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_list_sessions_filter_by_plan_version(client):
    pv_id = _setup(client)
    pv_id2 = _setup(client)
    client.post("/api/sessions", json={"plan_version_id": pv_id})
    client.post("/api/sessions", json={"plan_version_id": pv_id2})
    r = client.get(f"/api/sessions?plan_version_id={pv_id}")
    assert r.status_code == 200
    assert all(s["plan_version_id"] == pv_id for s in r.json())


def test_get_session(client):
    pv_id = _setup(client)
    session = client.post("/api/sessions", json={"plan_version_id": pv_id}).json()
    r = client.get(f"/api/sessions/{session['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == session["id"]


def test_get_session_not_found(client):
    r = client.get("/api/sessions/nonexistent")
    assert r.status_code == 404


def test_abort_pending_session(client):
    pv_id = _setup(client)
    session = client.post("/api/sessions", json={"plan_version_id": pv_id}).json()
    # pending sessions can be aborted
    r = client.post(f"/api/sessions/{session['id']}/abort")
    assert r.status_code == 200
    assert r.json()["status"] == "aborted"


def test_abort_already_completed_fails(client):
    pv_id = _setup(client)
    session = client.post("/api/sessions", json={"plan_version_id": pv_id}).json()
    # Manually force status to completed
    from app.models import Session as SessionModel
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    s = db.get(SessionModel, session["id"])
    s.status = "completed"
    db.commit()
    db.close()

    r = client.post(f"/api/sessions/{session['id']}/abort")
    assert r.status_code == 400


def test_session_run_fails_missing_env_var(client):
    """Running with a missing API key env var should immediately error the session."""
    import asyncio
    pv_id = _setup(client)
    session = client.post("/api/sessions", json={"plan_version_id": pv_id}).json()
    session_id = session["id"]

    # Override env to ensure key is absent
    import os
    os.environ.pop("TEST_KEY", None)

    # run_session is async; call it directly
    from app.services.agent_loop import run_session
    from tests.conftest import TestingSessionLocal

    asyncio.get_event_loop().run_until_complete(run_session(session_id, TestingSessionLocal))

    r = client.get(f"/api/sessions/{session_id}")
    assert r.json()["status"] == "errored"
    assert "TEST_KEY" in r.json()["termination_reason"]


def test_rerun_session(client):
    """Rerun creates a new session with the same plan_version_id."""
    pv_id = _setup(client)
    original = client.post("/api/sessions", json={"plan_version_id": pv_id}).json()
    r = client.post(f"/api/sessions/{original['id']}/rerun")
    assert r.status_code == 200
    data = r.json()
    assert data["original_session_id"] == original["id"]
    assert data["new_session_id"] != original["id"]
    assert data["plan_version_id"] == pv_id

    # The new session should exist and be pending
    new_session = client.get(f"/api/sessions/{data['new_session_id']}").json()
    assert new_session["status"] == "pending"
    assert new_session["plan_version_id"] == pv_id


def test_rerun_not_found(client):
    r = client.post("/api/sessions/nonexistent/rerun")
    assert r.status_code == 404


def test_rerun_and_run_missing_env(client):
    """rerun-and-run should create and start the session; missing env var errors it."""
    import asyncio
    import os
    pv_id = _setup(client)
    original = client.post("/api/sessions", json={"plan_version_id": pv_id}).json()

    os.environ.pop("TEST_KEY", None)

    r = client.post(f"/api/sessions/{original['id']}/rerun-and-run")
    assert r.status_code == 200
    new_id = r.json()["new_session_id"]

    # Background task may not fire in test client context — call run_session directly
    from app.services.agent_loop import run_session
    from tests.conftest import TestingSessionLocal
    asyncio.get_event_loop().run_until_complete(run_session(new_id, TestingSessionLocal))

    new_session = client.get(f"/api/sessions/{new_id}").json()
    assert new_session["status"] == "errored"
    assert "TEST_KEY" in new_session["termination_reason"]
