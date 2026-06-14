

TOOL_PAYLOAD = {
    "name": "search",
    "description": "A search tool",
    "tags": ["web"],
    "version": {
        "display_name": "search",
        "model_facing_description": "Search the web",
        "parameter_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
        "response_mode": "static",
        "static_response": {"results": ["foo", "bar"]},
    },
}


def test_create_tool(client):
    r = client.post("/api/tools", json=TOOL_PAYLOAD)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "search"
    assert len(data["versions"]) == 1
    assert data["versions"][0]["version_number"] == 1
    assert data["versions"][0]["display_name"] == "search"


def test_list_tools(client):
    client.post("/api/tools", json=TOOL_PAYLOAD)
    client.post("/api/tools", json={**TOOL_PAYLOAD, "name": "calculator"})
    r = client.get("/api/tools")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_tool(client):
    created = client.post("/api/tools", json=TOOL_PAYLOAD).json()
    r = client.get(f"/api/tools/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]


def test_get_tool_not_found(client):
    r = client.get("/api/tools/nonexistent")
    assert r.status_code == 404


def test_update_tool_meta(client):
    created = client.post("/api/tools", json=TOOL_PAYLOAD).json()
    r = client.patch(f"/api/tools/{created['id']}", json={"name": "renamed", "tags": ["updated"]})
    assert r.status_code == 200
    assert r.json()["name"] == "renamed"
    assert r.json()["tags"] == ["updated"]


def test_add_tool_version(client):
    created = client.post("/api/tools", json=TOOL_PAYLOAD).json()
    tool_id = created["id"]
    new_version = {
        "display_name": "search_v2",
        "model_facing_description": "Better search",
        "parameter_schema": {"type": "object", "properties": {"query": {"type": "string"}}},
        "response_mode": "static",
        "static_response": {"results": ["updated"]},
    }
    r = client.post(f"/api/tools/{tool_id}/versions", json=new_version)
    assert r.status_code == 201
    assert r.json()["version_number"] == 2
    assert r.json()["display_name"] == "search_v2"

    tool = client.get(f"/api/tools/{tool_id}").json()
    assert len(tool["versions"]) == 2


def test_delete_tool(client):
    created = client.post("/api/tools", json=TOOL_PAYLOAD).json()
    r = client.delete(f"/api/tools/{created['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/tools/{created['id']}").status_code == 404


def test_static_response_roundtrip(client):
    payload = {**TOOL_PAYLOAD}
    payload["version"]["static_response"] = {"nested": {"value": 42}, "list": [1, 2, 3]}
    created = client.post("/api/tools", json=payload).json()
    tv = created["versions"][0]
    assert tv["static_response"] == {"nested": {"value": 42}, "list": [1, 2, 3]}


def test_dynamic_tool_creation(client):
    payload = {
        "name": "counter",
        "description": "counts calls",
        "tags": [],
        "version": {
            "display_name": "counter",
            "model_facing_description": "Count invocations",
            "parameter_schema": {"type": "object", "properties": {}},
            "response_mode": "dynamic",
            "static_response": {},
            "dynamic_code": "def respond(args, context):\n    context['n'] = context.get('n', 0) + 1\n    return {'count': context['n']}",
        },
    }
    r = client.post("/api/tools", json=payload)
    assert r.status_code == 201
    assert r.json()["versions"][0]["response_mode"] == "dynamic"


def test_delete_tool_referenced_by_plan(client):
    """Deleting a tool should succeed even if a plan version references it (FK cascade)."""
    tool = client.post("/api/tools", json=TOOL_PAYLOAD).json()
    tv_id = tool["versions"][0]["id"]
    mc = client.post("/api/model-configs", json={
        "name": "m",
        "base_url": "https://api.openai.com/v1",
        "model_snapshot": "gpt-4o-mini",
        "api_key_env": "OPENAI_API_KEY",
    }).json()
    # Create a plan version that references this tool
    plan = client.post("/api/plans", json={
        "name": "p",
        "description": "",
        "version": {
            "model_config_id": mc["id"],
            "tool_version_ids": [tv_id],
            "system_prompt": "",
            "user_prompt": "hello",
        },
    }).json()
    pv_id = plan["versions"][0]["id"]

    # Deleting the tool should succeed (cascade cleans up plan_version_tools)
    r = client.delete(f"/api/tools/{tool['id']}")
    assert r.status_code == 204
    assert client.get(f"/api/tools/{tool['id']}").status_code == 404

    # Plan version should still exist (only the junction row is removed)
    pv = client.get(f"/api/plans/{plan['id']}").json()
    assert pv["versions"][0]["id"] == pv_id
