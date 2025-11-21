import uuid
from datetime import datetime, timedelta
from typing import Dict

from app.services.auth_service import AuthService


API_PREFIX = "/api/v1"


def _generate_credentials() -> Dict[str, str]:
    email = f"tester_{uuid.uuid4().hex}@example.com"
    password = "Str0ngPass!"
    return {"email": email, "password": password}


def _register_user(client) -> Dict[str, str]:
    creds = _generate_credentials()
    response = client.post(
        f"{API_PREFIX}/auth/register",
        params={"email": creds["email"], "password": creds["password"]},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    creds["user_id"] = data["user_id"]
    return creds


def _generate_api_key(client, username: str, password: str, plan_code: str = "PRO_M") -> str:
    response = client.post(
        f"{API_PREFIX}/auth/api-key",
        json={"username": username, "password": password, "plan_code": plan_code},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    return data["access_token"]


def _auth_headers(token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_public_endpoints(client):
    root_resp = client.get("/")
    assert root_resp.status_code == 200
    assert "message" in root_resp.json()

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"


def test_register_and_login_flow(client):
    creds = _register_user(client)

    # Duplicate registration should fail
    duplicate = client.post(
        f"{API_PREFIX}/auth/register",
        params={"email": creds["email"], "password": creds["password"]},
    )
    assert duplicate.status_code == 400

    # Test API key generation with PRO_M plan
    api_key_m = _generate_api_key(client, creds["email"], creds["password"], "PRO_M")
    headers_m = _auth_headers(api_key_m)

    me_resp = client.get(f"{API_PREFIX}/auth/me", headers=headers_m)
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == creds["email"].lower()
    assert me_resp.json()["access_token"] == api_key_m
    assert me_resp.json()["plan_code"] == "PRO_M"

    # Test API key generation with PRO_Y plan
    api_key_y = _generate_api_key(client, creds["email"], creds["password"], "PRO_Y")
    headers_y = _auth_headers(api_key_y)

    me_resp_y = client.get(f"{API_PREFIX}/auth/me", headers=headers_y)
    assert me_resp_y.status_code == 200
    assert me_resp_y.json()["email"] == creds["email"].lower()
    assert me_resp_y.json()["access_token"] == api_key_y
    assert me_resp_y.json()["plan_code"] == "PRO_Y"


def test_api_key_trial_plan_via_password_flow(client):
    creds = _register_user(client)

    response = client.post(
        f"{API_PREFIX}/auth/api-key",
        json={"username": creds["email"], "password": creds["password"], "plan_code": "TRIAL"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["plan_code"] == "TRIAL"

    expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
    remaining = expires_at - datetime.utcnow()
    assert remaining >= timedelta(days=13)
    assert remaining <= timedelta(days=15)



def test_trial_api_key_endpoint(client):
    ip_address = "203.0.113.5"
    response = client.post(
        f"{API_PREFIX}/auth/api-key/trial",
        json={"ip_user": ip_address},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["plan_code"] == "TRIAL"
    assert data["user_id"]
    assert data["access_token"]

    second_response = client.post(
        f"{API_PREFIX}/auth/api-key/trial",
        json={"ip_user": ip_address},
    )
    assert second_response.status_code == 201, second_response.text
    second_data = second_response.json()
    assert second_data["access_token"] == data["access_token"]
    assert second_data["user_id"] == data["user_id"]

    invalid_response = client.post(
        f"{API_PREFIX}/auth/api-key/trial",
        json={"ip_user": "not-an-ip"},
    )
    assert invalid_response.status_code == 400


def test_google_auth_endpoints(client, monkeypatch):
    creds = _register_user(client)
    api_key = _generate_api_key(client, creds["email"], creds["password"])
    headers = _auth_headers(api_key)

    fake_state = "state-token"

    def fake_create_google_auth_url(
        self, user_id: str, scopes, include_granted_scopes=False, agent_id=None
    ):
        assert user_id
        assert scopes
        return {"auth_url": "https://accounts.example.com/oauth", "state": fake_state}

    def fake_exchange_google_code(self, code: str, state: str):
        assert code
        assert state == fake_state
        return {
            "access_token": "google-access",
            "refresh_token": "google-refresh",
            "scope": ["scope1", "scope2"],
            "expires_at": datetime.utcnow() + timedelta(hours=1),
            "email": f"google_{uuid.uuid4().hex}@example.com",
        }

    monkeypatch.setattr(AuthService, "create_google_auth_url", fake_create_google_auth_url)
    monkeypatch.setattr(AuthService, "exchange_google_code", fake_exchange_google_code)

    auth_resp = client.post(
        f"{API_PREFIX}/auth/google/auth",
        headers=headers,
        json={"email": creds["email"]},
    )
    assert auth_resp.status_code == 200
    auth_data = auth_resp.json()
    assert auth_data["state"] == fake_state

    get_auth_resp = client.get(
        f"{API_PREFIX}/auth/google/auth", headers=headers
    )
    assert get_auth_resp.status_code == 200
    assert get_auth_resp.json()["state"] == fake_state

    callback_resp = client.get(
        f"{API_PREFIX}/auth/google/callback",
        params={"code": "test-code", "state": fake_state},
    )
    assert callback_resp.status_code == 200
    callback_data = callback_resp.json()
    assert callback_data["message"] == "Google authentication successful"


def test_google_status_returns_auth_url_when_missing_token(client, monkeypatch):
    creds = _register_user(client)
    api_key = _generate_api_key(client, creds["email"], creds["password"])
    headers = _auth_headers(api_key)

    expected_state = "state-token"
    expected_url = "https://accounts.example.com/oauth"

    def fake_create_google_auth_url(
        self, user_id: str, scopes, include_granted_scopes=False, agent_id=None
    ):
        assert user_id
        assert scopes
        return {"auth_url": expected_url, "state": expected_state}

    monkeypatch.setattr(
        AuthService,
        "create_google_auth_url",
        fake_create_google_auth_url,
    )

    resp = client.get(f"{API_PREFIX}/auth/google", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_required"] is True
    assert data["auth_url"] == expected_url
    assert data["auth_state"] == expected_state
    assert data["tokens"] == []
    assert data["required_scopes"]


def test_google_status_respects_tool_scopes(client, monkeypatch):
    creds = _register_user(client)
    api_key = _generate_api_key(client, creds["email"], creds["password"])
    headers = _auth_headers(api_key)

    captured_scopes = {}

    def fake_create_google_auth_url(
        self, user_id: str, scopes, include_granted_scopes=False, agent_id=None
    ):
        captured_scopes["value"] = scopes
        return {
            "auth_url": "https://accounts.example.com/oauth",
            "state": "state-token",
        }

    monkeypatch.setattr(
        AuthService,
        "create_google_auth_url",
        fake_create_google_auth_url,
    )

    resp = client.get(
        f"{API_PREFIX}/auth/google",
        headers=headers,
        params={"tools": "gmail_read_messages"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_required"] is True
    assert captured_scopes["value"] == [
        "https://www.googleapis.com/auth/gmail.readonly"
    ]
    assert data["required_scopes"] == [
        "https://www.googleapis.com/auth/gmail.readonly"
    ]


def test_google_status_accepts_body_scopes(client, monkeypatch):
    creds = _register_user(client)
    api_key = _generate_api_key(client, creds["email"], creds["password"])
    headers = _auth_headers(api_key)

    captured_scopes = {}

    def fake_create_google_auth_url(
        self, user_id: str, scopes, include_granted_scopes=False, agent_id=None
    ):
        captured_scopes["value"] = scopes
        return {
            "auth_url": "https://accounts.example.com/oauth",
            "state": "state-token",
        }

    monkeypatch.setattr(
        AuthService,
        "create_google_auth_url",
        fake_create_google_auth_url,
    )

    body_scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    resp = client.post(
        f"{API_PREFIX}/auth/google",
        headers=headers,
        json={"scopes": body_scopes},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["auth_required"] is True
    assert captured_scopes["value"] == body_scopes
    assert data["required_scopes"] == body_scopes


def test_refresh_status_google_uses_agent_scopes(client, monkeypatch):
    creds = _register_user(client)
    api_key = _generate_api_key(client, creds["email"], creds["password"])
    headers = _auth_headers(api_key)

    create_payload = {
        "name": "Gmail Agent",
        "tools": ["gmail_read_messages"],
        "config": {
            "llm_model": "gpt-4o-mini",
            "temperature": 0.2,
            "max_tokens": 256,
            "memory_type": "buffer",
            "reasoning_strategy": "react",
        },
    }
    create_resp = client.post(
        f"{API_PREFIX}/agents/", headers=headers, json=create_payload
    )
    assert create_resp.status_code == 200
    agent_id = create_resp.json()["id"]

    refreshed_calls = []
    token_calls = []
    dummy_token = type("Token", (), {"service": "google", "scope": ["https://www.googleapis.com/auth/gmail.readonly"]})
    dummy_global_token = type("Token", (), {"service": "google", "scope": ["https://www.googleapis.com/auth/gmail.readonly", "scopeX"]})

    def fake_refresh_google_token(self, user_id: str, agent_id: str | None = None):
        refreshed_calls.append((user_id, agent_id))
        return None

    def fake_get_user_auth_tokens(self, user_id: str, agent_id: str | None = None):
        token_calls.append(agent_id)
        if agent_id:
            return []
        return [dummy_token(), dummy_global_token()]

    monkeypatch.setattr(AuthService, "refresh_google_token", fake_refresh_google_token)
    monkeypatch.setattr(AuthService, "get_user_auth_tokens", fake_get_user_auth_tokens)

    resp = client.post(
        f"{API_PREFIX}/auth/refresh-status-google",
        headers=headers,
        json={"agent_id": agent_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == agent_id
    assert data["status"] == "Authenticated"
    assert data["refreshed"] is False
    assert data["missing_scopes"] == []
    assert data["granted_scopes"] == [
        "https://www.googleapis.com/auth/gmail.readonly",
        "scopeX",
    ]
    assert refreshed_calls == [
        (creds["user_id"], agent_id),
        (creds["user_id"], None),
    ]
    assert token_calls == [agent_id, None]


def test_refresh_status_google_skips_oauth_when_no_google_tools(client):
    creds = _register_user(client)
    api_key = _generate_api_key(client, creds["email"], creds["password"])
    headers = _auth_headers(api_key)

    create_payload = {
        "name": "File Agent",
        "tools": ["file_list"],
        "config": {
            "llm_model": "gpt-4o-mini",
            "temperature": 0.2,
            "max_tokens": 256,
            "memory_type": "buffer",
            "reasoning_strategy": "react",
        },
    }
    create_resp = client.post(
        f"{API_PREFIX}/agents/", headers=headers, json=create_payload
    )
    assert create_resp.status_code == 200
    agent_id = create_resp.json()["id"]

    resp = client.post(
        f"{API_PREFIX}/auth/refresh-status-google",
        headers=headers,
        json={"agent_id": agent_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_id"] == agent_id
    assert data["status"] == "Authenticated"
    assert data["refreshed"] is False
    assert data["granted_scopes"] == []
    assert data["missing_scopes"] == []
    assert data["required_scopes"] == []


def test_refresh_status_google_uses_global_when_agent_token_insufficient(client, monkeypatch):
    creds = _register_user(client)
    api_key = _generate_api_key(client, creds["email"], creds["password"])
    headers = _auth_headers(api_key)

    create_payload = {
        "name": "Sheets Agent",
        "tools": ["google_sheets_get_values"],
        "config": {
            "llm_model": "gpt-4o-mini",
            "temperature": 0.2,
            "max_tokens": 256,
            "memory_type": "buffer",
            "reasoning_strategy": "react",
        },
    }
    create_resp = client.post(
        f"{API_PREFIX}/agents/", headers=headers, json=create_payload
    )
    assert create_resp.status_code == 200
    agent_id = create_resp.json()["id"]

    refreshed_calls = []
    token_calls = []
    insufficient_agent_token = type(
        "Token",
        (),
        {"service": "google", "scope": ["https://www.googleapis.com/auth/gmail.readonly"]},
    )
    full_global_token = type(
        "Token",
        (),
        {"service": "google", "scope": ["https://www.googleapis.com/auth/spreadsheets.readonly"]},
    )

    def fake_refresh_google_token(self, user_id: str, agent_id: str | None = None):
        refreshed_calls.append((user_id, agent_id))
        return None

    def fake_get_user_auth_tokens(self, user_id: str, agent_id: str | None = None):
        token_calls.append(agent_id)
        if agent_id:
            return [insufficient_agent_token()]
        return [full_global_token()]

    monkeypatch.setattr(AuthService, "refresh_google_token", fake_refresh_google_token)
    monkeypatch.setattr(AuthService, "get_user_auth_tokens", fake_get_user_auth_tokens)

    resp = client.post(
        f"{API_PREFIX}/auth/refresh-status-google",
        headers=headers,
        json={"agent_id": agent_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "Authenticated"
    assert data["refreshed"] is False
    assert data["missing_scopes"] == []
    assert set(data["granted_scopes"]) == {
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
    }
    assert refreshed_calls == [
        (creds["user_id"], agent_id),
        (creds["user_id"], None),
    ]
    assert token_calls == [agent_id, None]


def test_google_auth_post_accepts_body_scopes(client, monkeypatch):
    creds = _register_user(client)
    api_key = _generate_api_key(client, creds["email"], creds["password"])
    headers = _auth_headers(api_key)

    captured_scopes = {}

    def fake_create_google_auth_url(
        self, user_id: str, scopes, include_granted_scopes=False, agent_id=None
    ):
        captured_scopes["value"] = scopes
        return {
            "auth_url": "https://accounts.example.com/oauth",
            "state": "state-token",
        }

    monkeypatch.setattr(
        AuthService,
        "create_google_auth_url",
        fake_create_google_auth_url,
    )

    body_scopes = ["https://www.googleapis.com/auth/gmail.readonly"]
    resp = client.post(
        f"{API_PREFIX}/auth/google/auth",
        headers=headers,
        json={"scopes": body_scopes},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert captured_scopes["value"] == body_scopes
    assert data["required_scopes"] == body_scopes


def test_tool_endpoints(client, tmp_path):
    creds = _register_user(client)
    headers = _auth_headers(creds["token"])

    list_resp = client.get(f"{API_PREFIX}/tools/", headers=headers)
    assert list_resp.status_code == 200
    tools = list_resp.json()
    assert tools, "Expected built-in tools to be initialised"

    tool_names = {tool["name"] for tool in tools}
    assert {"file_list", "docx", "spreadsheet"}.issubset(tool_names)

    builtin_tools_resp = client.get(
        f"{API_PREFIX}/tools/", headers=headers, params={"tool_type": "builtin"}
    )
    assert builtin_tools_resp.status_code == 200

    schema_resp = client.get(f"{API_PREFIX}/tools/schemas/gmail", headers=headers)
    assert schema_resp.status_code == 200
    assert schema_resp.json()["type"] == "object"

    scopes_resp = client.get(
        f"{API_PREFIX}/tools/scopes/required",
        headers=headers,
        params={"tools": "gmail,google_sheets"},
    )
    assert scopes_resp.status_code == 200
    assert scopes_resp.json()["scopes"]

    file_list_tool = next(tool for tool in tools if tool["name"] == "file_list")

    example_file = tmp_path / "example.txt"
    example_file.write_text("hello from tests")

    execute_builtin = client.post(
        f"{API_PREFIX}/tools/execute",
        headers=headers,
        json={
            "tool_id": file_list_tool["id"],
            "parameters": {"directory": str(tmp_path)},
        },
    )
    assert execute_builtin.status_code == 200
    builtin_data = execute_builtin.json()
    assert builtin_data["success"] is True
    assert builtin_data["result"]["count"] == 1

    custom_payload = {
        "name": "echo_tool",
        "description": "Echo back provided text",
        "schema": {
            "type": "object",
            "properties": {"echo": {"type": "string"}},
            "required": ["echo"],
        },
        "type": "custom",
    }

    create_resp = client.post(
        f"{API_PREFIX}/tools/", headers=headers, json=custom_payload
    )
    assert create_resp.status_code == 200
    custom_tool = create_resp.json()

    get_resp = client.get(f"{API_PREFIX}/tools/{custom_tool['id']}", headers=headers)
    assert get_resp.status_code == 200

    update_resp = client.put(
        f"{API_PREFIX}/tools/{custom_tool['id']}",
        headers=headers,
        json={"description": "Updated description"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["description"] == "Updated description"

    execute_custom = client.post(
        f"{API_PREFIX}/tools/execute",
        headers=headers,
        json={
            "tool_id": custom_tool["id"],
            "parameters": {"echo": "ping"},
        },
    )
    assert execute_custom.status_code == 200
    execute_custom_data = execute_custom.json()
    assert execute_custom_data["success"] is True
    assert execute_custom_data["result"]["parameters"]["echo"] == "ping"

    delete_resp = client.delete(
        f"{API_PREFIX}/tools/{custom_tool['id']}", headers=headers
    )
    assert delete_resp.status_code == 200

    missing_resp = client.get(
        f"{API_PREFIX}/tools/{custom_tool['id']}", headers=headers
    )
    assert missing_resp.status_code == 404


def test_agent_endpoints(client):
    creds = _register_user(client)
    headers = _auth_headers(creds["token"])

    # Ensure built-in tools exist for agent tool validation
    client.get(f"{API_PREFIX}/tools/", headers=headers)

    create_payload = {
        "name": "Research Assistant",
        "tools": ["file_list"],
        "config": {
            "llm_model": "gpt-4o-mini",
            "temperature": 0.2,
            "max_tokens": 256,
            "memory_type": "buffer",
            "reasoning_strategy": "react",
        },
    }

    create_resp = client.post(
        f"{API_PREFIX}/agents/", headers=headers, json=create_payload
    )
    assert create_resp.status_code == 200
    agent = create_resp.json()
    agent_id = agent["id"]
    assert agent["auth_required"] is False
    assert agent.get("auth_url") is None

    list_resp = client.get(f"{API_PREFIX}/agents/", headers=headers)
    assert list_resp.status_code == 200
    assert any(a["id"] == agent_id for a in list_resp.json())

    get_resp = client.get(f"{API_PREFIX}/agents/{agent_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == create_payload["name"]

    update_resp = client.put(
        f"{API_PREFIX}/agents/{agent_id}",
        headers=headers,
        json={"name": "Updated Agent"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Updated Agent"

    execute_resp = client.post(
        f"{API_PREFIX}/agents/{agent_id}/execute",
        headers=headers,
        json={
            "input": "Summarise the latest news",
            "parameters": {"max_steps": 2},
            "session_id": "test-session",
        },
    )
    assert execute_resp.status_code == 200
    execution_id = execute_resp.json()["execution_id"]
    assert execution_id

    exec_list_resp = client.get(
        f"{API_PREFIX}/agents/{agent_id}/executions", headers=headers
    )
    assert exec_list_resp.status_code == 200
    exec_history = exec_list_resp.json()["executions"]
    assert exec_history
    assert exec_history[0]["status"] in {"completed", "failed"}

    stats_resp = client.get(
        f"{API_PREFIX}/agents/executions/stats", headers=headers
    )
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total_executions"] >= 1

    delete_resp = client.delete(
        f"{API_PREFIX}/agents/{agent_id}", headers=headers
    )
    assert delete_resp.status_code == 200

    missing_resp = client.get(f"{API_PREFIX}/agents/{agent_id}", headers=headers)
    assert missing_resp.status_code == 404
