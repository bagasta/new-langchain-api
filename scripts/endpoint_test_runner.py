#!/usr/bin/env python3

"""
Automated endpoint regression tester for the LangChain Agent API.

The script walks through every public endpoint, exercising authentication,
tool management, agent lifecycle (including Google-backed tools), and
optional OAuth callback verification. It is intended for manual execution
against a running API instance.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx


@dataclass
class StepResult:
    name: str
    status: str
    detail: str = ""


class SkipStep(Exception):
    """Raised when a step is intentionally skipped."""


class ApiTestRunner:
    def __init__(
        self,
        base_url: str,
        api_prefix: str,
        email: str,
        password: str,
        plan_code: str,
        google_auth_code: Optional[str],
        google_auth_state: Optional[str],
        open_browser: bool,
        timeout: float,
        verify_ssl: bool,
    ):
        self.client = httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=timeout,
            verify=verify_ssl,
            follow_redirects=True,
        )
        self.api_prefix = api_prefix.rstrip("/")
        self.email = email
        self.password = password
        self.plan_code = plan_code
        self.google_auth_code = google_auth_code
        self.google_auth_state_override = google_auth_state
        self.open_browser = open_browser
        self.results: List[StepResult] = []

        self.login_token: Optional[str] = None
        self.api_key_token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.google_auth_state: Optional[str] = None
        self.google_auth_url: Optional[str] = None
        self.primary_agent_id: Optional[str] = None
        self.google_agent_id: Optional[str] = None

    # Public API -----------------------------------------------------------------

    def run(self) -> List[StepResult]:
        steps: List[tuple[str, Callable[[], Optional[str]]]] = [
            ("Public endpoints", self.test_public_endpoints),
            ("User registration & activation", self.ensure_user_ready),
            ("Login & profile", self.login_and_profile),
            ("API key lifecycle", self.manage_api_key),
            ("Auth tokens & password update", self.test_auth_token_endpoints),
            ("Tool endpoints", self.test_tool_endpoints),
            ("Agent endpoints", self.test_agent_endpoints),
            ("Google authentication", self.test_google_auth_flow),
        ]

        for title, func in steps:
            self._execute_step(title, func)

        return self.results

    # Internal helpers -----------------------------------------------------------

    def _execute_step(self, name: str, func: Callable[[], Optional[str]]) -> None:
        try:
            detail = func() or ""
        except SkipStep as skip:
            self.results.append(StepResult(name=name, status="skipped", detail=str(skip)))
        except Exception as exc:
            self.results.append(StepResult(name=name, status="failed", detail=str(exc)))
        else:
            self.results.append(StepResult(name=name, status="passed", detail=detail))

    def _api(self, path: str) -> str:
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.api_prefix}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        expected_status: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        response = self.client.request(
            method,
            path,
            headers=headers,
            params=params,
            json=json_body,
            data=data,
            files=files,
        )
        status_text = f"{method.upper()} {path} -> {response.status_code}"
        if expected_status is not None and response.status_code != expected_status:
            raise AssertionError(
                f"{status_text} (expected {expected_status})\n"
                f"Response: {response.text}"
            )
        print(status_text)
        return response

    # Step implementations -------------------------------------------------------

    def test_public_endpoints(self) -> str:
        root_resp = self._request("GET", "/", expected_status=200)
        health_resp = self._request("GET", "/health", expected_status=200)
        summary = {
            "root": root_resp.json(),
            "health": health_resp.json(),
        }
        return json.dumps(summary, default=str)

    def ensure_user_ready(self) -> str:
        statements: List[str] = []

        register_resp = self._request(
            "POST",
            self._api("/auth/register"),
            params={"email": self.email, "password": self.password},
        )
        if register_resp.status_code == 200:
            payload = register_resp.json()
            self.user_id = payload.get("user_id")
            statements.append("registered new user")
        elif register_resp.status_code == 400 and "already" in register_resp.text.lower():
            statements.append("user already registered")
        else:
            raise AssertionError(f"Registration failed: {register_resp.text}")

        activate_resp = self._request(
            "POST",
            self._api("/auth/activate"),
            params={"email": self.email},
        )
        if activate_resp.status_code == 200:
            payload = activate_resp.json()
            self.user_id = self.user_id or payload.get("user_id")
            statements.append("activated user")
        elif activate_resp.status_code == 400 and "already active" in activate_resp.text.lower():
            statements.append("user already active")
        else:
            raise AssertionError(f"Activation failed: {activate_resp.text}")

        return ", ".join(statements)

    def login_and_profile(self) -> str:
        login_resp = self._request(
            "POST",
            self._api("/auth/login"),
            params={"email": self.email, "password": self.password},
        )
        if login_resp.status_code != 200:
            raise AssertionError(f"Login failed: {login_resp.text}")

        self.login_token = login_resp.json().get("jwt_token")
        if not self.login_token:
            raise AssertionError("Login succeeded but no jwt token returned")

        headers = {"Authorization": f"Bearer {self.login_token}"}
        me_resp = self._request(
            "GET",
            self._api("/auth/me"),
            headers=headers,
            expected_status=200,
        )
        me_payload = me_resp.json()
        self.user_id = self.user_id or me_payload.get("id")
        created_at = me_payload.get("created_at")
        return f"login OK, user_id={self.user_id}, created_at={created_at}"

    def manage_api_key(self) -> str:
        if not self.login_token:
            raise AssertionError("Login token missing; cannot create API key")

        api_key_resp = self._request(
            "POST",
            self._api("/auth/api-key"),
            json_body={
                "username": self.email,
                "password": self.password,
                "plan_code": self.plan_code,
            },
        )
        if api_key_resp.status_code != 200:
            raise AssertionError(f"API key creation failed: {api_key_resp.text}")

        api_payload = api_key_resp.json()
        self.api_key_token = api_payload.get("access_token")
        if not self.api_key_token:
            raise AssertionError("API key response missing access token")

        me_resp = self._request(
            "GET",
            self._api("/auth/me"),
            headers={"Authorization": f"Bearer {self.api_key_token}"},
            expected_status=200,
        )
        me_payload = me_resp.json()
        api_summary = {
            "plan": api_payload.get("plan_code"),
            "expires_at": api_payload.get("expires_at"),
            "me_email": me_payload.get("email"),
        }
        return json.dumps(api_summary)

    def test_auth_token_endpoints(self) -> str:
        if not self.login_token or not self.api_key_token or not self.user_id:
            raise AssertionError("Missing authentication context for auth token tests")

        login_headers = {"Authorization": f"Bearer {self.login_token}"}
        api_headers = {"Authorization": f"Bearer {self.api_key_token}"}

        tokens_resp = self._request(
            "GET",
            self._api("/auth/tokens"),
            headers=login_headers,
            expected_status=200,
        )

        update_resp = self._request(
            "POST",
            self._api("/auth/api-key/update"),
            headers=login_headers,
            json_body={
                "username": self.email,
                "password": self.password,
                "access_token": self.api_key_token,
                "plan_code": self.plan_code,
            },
        )
        if update_resp.status_code != 200:
            raise AssertionError(f"API key update failed: {update_resp.text}")

        password_resp = self._request(
            "POST",
            self._api("/auth/user/update-password"),
            headers=login_headers,
            json_body={"user_id": self.user_id, "new_password": self.password},
        )
        if password_resp.status_code != 200:
            raise AssertionError(f"Password update failed: {password_resp.text}")

        return json.dumps(
            {
                "tokens_count": len(tokens_resp.json().get("tokens", [])),
                "api_key_extended": update_resp.json(),
                "password_updated": password_resp.json(),
            }
        )

    def test_tool_endpoints(self) -> str:
        if not self.api_key_token:
            raise AssertionError("API key token missing; cannot access tool endpoints")

        headers = {"Authorization": f"Bearer {self.api_key_token}"}

        tools_resp = self._request(
            "GET",
            self._api("/tools/"),
            headers=headers,
            expected_status=200,
        )
        tools = tools_resp.json()
        if not tools:
            raise AssertionError("Tool list is empty; built-in tools should exist")

        builtin_resp = self._request(
            "GET",
            self._api("/tools/"),
            headers=headers,
            params={"tool_type": "builtin"},
            expected_status=200,
        )

        schema_resp = self._request(
            "GET",
            self._api("/tools/schemas/gmail"),
            headers=headers,
            expected_status=200,
        )

        scopes_resp = self._request(
            "GET",
            self._api("/tools/scopes/required"),
            headers=headers,
            params={"tools": "gmail,google_sheets"},
            expected_status=200,
        )

        file_list_tool = next((tool for tool in tools if tool.get("name") == "file_list"), None)
        if not file_list_tool:
            raise AssertionError("file_list tool not found in built-in tool catalogue")

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            (tmp_path / "example.txt").write_text("hello from endpoint tester\n", encoding="utf-8")
            execute_resp = self._request(
                "POST",
                self._api("/tools/execute"),
                headers=headers,
                json_body={
                    "tool_id": file_list_tool["id"],
                    "parameters": {"directory": str(tmp_path)},
                },
            )
            if execute_resp.status_code != 200:
                raise AssertionError(f"Executing built-in tool failed: {execute_resp.text}")

        custom_payload = {
            "name": f"echo_tool_{self.user_id or 'test'}",
            "description": "Echo back provided text",
            "schema": {
                "type": "object",
                "properties": {"echo": {"type": "string"}},
                "required": ["echo"],
            },
            "type": "custom",
        }

        create_resp = self._request(
            "POST",
            self._api("/tools/"),
            headers=headers,
            json_body=custom_payload,
        )
        if create_resp.status_code != 200:
            raise AssertionError(f"Creating custom tool failed: {create_resp.text}")
        custom_tool = create_resp.json()
        custom_tool_id = custom_tool["id"]

        self._request(
            "GET",
            self._api(f"/tools/{custom_tool_id}"),
            headers=headers,
            expected_status=200,
        )

        update_resp = self._request(
            "PUT",
            self._api(f"/tools/{custom_tool_id}"),
            headers=headers,
            json_body={"description": "Updated description"},
        )
        if update_resp.status_code != 200 or update_resp.json().get("description") != "Updated description":
            raise AssertionError("Updating custom tool failed")

        execute_custom_resp = self._request(
            "POST",
            self._api("/tools/execute"),
            headers=headers,
            json_body={
                "tool_id": custom_tool_id,
                "parameters": {"echo": "ping"},
            },
        )
        if execute_custom_resp.status_code != 200:
            raise AssertionError(f"Executing custom tool failed: {execute_custom_resp.text}")

        delete_resp = self._request(
            "DELETE",
            self._api(f"/tools/{custom_tool_id}"),
            headers=headers,
        )
        if delete_resp.status_code != 200:
            raise AssertionError(f"Deleting custom tool failed: {delete_resp.text}")

        missing_resp = self._request(
            "GET",
            self._api(f"/tools/{custom_tool_id}"),
            headers=headers,
        )
        if missing_resp.status_code != 404:
            raise AssertionError("Deleted tool still retrievable; expected 404")

        return json.dumps(
            {
                "tool_count": len(tools),
                "builtin_filter": len(builtin_resp.json()),
                "gmail_schema_keys": list(schema_resp.json().keys()),
                "required_scopes": scopes_resp.json().get("scopes", []),
            }
        )

    def test_agent_endpoints(self) -> str:
        if not self.api_key_token:
            raise AssertionError("API key token missing; cannot exercise agent endpoints")

        headers = {"Authorization": f"Bearer {self.api_key_token}"}

        create_payload = {
            "name": "Endpoint Tester Agent",
            "tools": ["file_list"],
            "config": {
                "llm_model": "gpt-4o-mini",
                "temperature": 0.2,
                "max_tokens": 128,
                "memory_type": "buffer",
                "reasoning_strategy": "react",
            },
        }
        create_resp = self._request(
            "POST",
            self._api("/agents/"),
            headers=headers,
            json_body=create_payload,
        )
        if create_resp.status_code != 200:
            raise AssertionError(f"Agent creation failed: {create_resp.text}")
        agent = create_resp.json()
        self.primary_agent_id = agent["id"]

        list_resp = self._request(
            "GET",
            self._api("/agents/"),
            headers=headers,
            expected_status=200,
        )

        get_resp = self._request(
            "GET",
            self._api(f"/agents/{self.primary_agent_id}"),
            headers=headers,
            expected_status=200,
        )

        update_resp = self._request(
            "PUT",
            self._api(f"/agents/{self.primary_agent_id}"),
            headers=headers,
            json_body={"name": "Endpoint Tester Agent Updated"},
        )
        if update_resp.status_code != 200:
            raise AssertionError(f"Updating agent failed: {update_resp.text}")

        doc_summary = "skipped"
        try:
            doc_resp = self._request(
                "POST",
                self._api(f"/agents/{self.primary_agent_id}/documents"),
                headers=headers,
                files={"file": ("sample.txt", b"Sample document content for ingestion.", "text/plain")},
            )
            if doc_resp.status_code == 200:
                doc_summary = "uploaded"
            else:
                doc_summary = f"failed ({doc_resp.status_code})"
        except Exception as exc:
            doc_summary = f"error: {exc}"

        execute_summary = "not attempted"
        try:
            execute_resp = self._request(
                "POST",
                self._api(f"/agents/{self.primary_agent_id}/execute"),
                headers=headers,
                json_body={
                    "input": "Provide a short status update.",
                    "parameters": {"max_steps": 1},
                    "session_id": "endpoint-test-session",
                },
            )
            if execute_resp.status_code == 200:
                execute_summary = execute_resp.json().get("status", "unknown")
            else:
                execute_summary = f"failed ({execute_resp.status_code})"
        except Exception as exc:
            execute_summary = f"error: {exc}"

        self._request(
            "GET",
            self._api(f"/agents/{self.primary_agent_id}/executions"),
            headers=headers,
            expected_status=200,
        )

        stats_resp = self._request(
            "GET",
            self._api("/agents/executions/stats"),
            headers=headers,
            expected_status=200,
        )

        delete_resp = self._request(
            "DELETE",
            self._api(f"/agents/{self.primary_agent_id}"),
            headers=headers,
        )
        if delete_resp.status_code != 200:
            raise AssertionError(f"Deleting agent failed: {delete_resp.text}")

        missing_resp = self._request(
            "GET",
            self._api(f"/agents/{self.primary_agent_id}"),
            headers=headers,
        )
        if missing_resp.status_code != 404:
            raise AssertionError("Deleted agent still retrievable; expected 404")

        google_resp = self._request(
            "POST",
            self._api("/agents/"),
            headers=headers,
            json_body={
                "name": "Google Tools Agent",
                "tools": ["gmail", "google_sheets"],
            },
        )
        if google_resp.status_code == 200:
            google_agent = google_resp.json()
            self.google_agent_id = google_agent["id"]
            self.google_auth_state = google_agent.get("auth_state") or self.google_auth_state
            self.google_auth_url = google_agent.get("auth_url")
        else:
            raise AssertionError(f"Creating Google-enabled agent failed: {google_resp.text}")

        if self.google_agent_id:
            self._request(
                "DELETE",
                self._api(f"/agents/{self.google_agent_id}"),
                headers=headers,
            )

        return json.dumps(
            {
                "agents_total": len(list_resp.json()),
                "document_upload": doc_summary,
                "execution_status": execute_summary,
                "stats": stats_resp.json(),
                "google_auth_required": bool(self.google_auth_url),
            }
        )

    def test_google_auth_flow(self) -> str:
        if not self.login_token:
            raise AssertionError("Login token missing; cannot initiate Google auth")

        headers = {"Authorization": f"Bearer {self.login_token}"}

        post_resp = self._request(
            "POST",
            self._api("/auth/google/auth"),
            headers=headers,
            json_body={"email": self.email},
        )
        if post_resp.status_code != 200:
            raise AssertionError(f"Google auth (POST) failed: {post_resp.text}")
        post_payload = post_resp.json()
        self.google_auth_state = self.google_auth_state or post_payload.get("state")
        self.google_auth_url = self.google_auth_url or post_payload.get("auth_url")

        get_resp = self._request(
            "GET",
            self._api("/auth/google/auth"),
            headers=headers,
            expected_status=200,
        )
        get_payload = get_resp.json()
        self.google_auth_state = self.google_auth_state or get_payload.get("state")
        self.google_auth_url = self.google_auth_url or get_payload.get("auth_url")

        if not self.google_auth_url or not self.google_auth_state:
            raise AssertionError("Google auth URL or state missing from responses")

        if self.open_browser:
            try:
                import webbrowser

                webbrowser.open(self.google_auth_url)
            except Exception as exc:
                print(f"Failed to open browser automatically: {exc}", file=sys.stderr)

        detail_lines = [
            "Initiated Google OAuth flow.",
            f"Auth URL: {self.google_auth_url}",
            f"State: {self.google_auth_state}",
        ]

        auth_state = self.google_auth_state_override or self.google_auth_state
        auth_code = self.google_auth_code
        if auth_code:
            callback_resp = self._request(
                "GET",
                self._api("/auth/google/callback"),
                params={"code": auth_code, "state": auth_state},
            )
            if callback_resp.status_code != 200:
                raise AssertionError(f"Google callback failed: {callback_resp.text}")
            detail_lines.append("Callback exchange succeeded.")
        else:
            detail_lines.append(
                "Callback skipped (provide --google-auth-code once you authorise the app)."
            )
            raise SkipStep("\n".join(detail_lines))

        return "\n".join(detail_lines)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run automated endpoint tests against a LangChain Agent API instance.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Example usage:
              python scripts/endpoint_test_runner.py --base-url http://localhost:8000 \\
                  --email bagasbgs2516@gmail.com --password Binatanglaut123 --open-browser

            To complete the Google OAuth callback automatically, obtain the 'code' parameter
            returned to the configured redirect URI and pass it back via --google-auth-code.
            """
        ),
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Root URL of the running API (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--api-prefix",
        default="/api/v1",
        help="API prefix corresponding to API_V1_STR (default: /api/v1)",
    )
    parser.add_argument(
        "--email",
        required=True,
        help="User email used for registration/login and Google OAuth initiation.",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Plaintext password used for registration/login.",
    )
    parser.add_argument(
        "--plan-code",
        default="PRO_M",
        choices=["PRO_M", "PRO_Y"],
        help="Subscription plan code used when generating API keys.",
    )
    parser.add_argument(
        "--google-auth-code",
        help="Optional OAuth code returned by Google to complete the callback exchange.",
    )
    parser.add_argument(
        "--google-auth-state",
        help="Optional override for the OAuth state returned by Google.",
    )
    parser.add_argument(
        "--open-browser",
        action="store_true",
        help="Automatically open the Google OAuth URL in the default browser.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP request timeout, in seconds (default: 30).",
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Disable TLS certificate verification (useful for self-signed endpoints).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    runner = ApiTestRunner(
        base_url=args.base_url,
        api_prefix=args.api_prefix,
        email=args.email,
        password=args.password,
        plan_code=args.plan_code,
        google_auth_code=args.google_auth_code,
        google_auth_state=args.google_auth_state,
        open_browser=args.open_browser,
        timeout=args.timeout,
        verify_ssl=not args.no_verify_ssl,
    )

    results = runner.run()
    print("\n=== Endpoint Test Summary ===")
    failures = 0
    for result in results:
        status = result.status.upper()
        print(f"- {result.name}: {status}")
        if result.detail:
            formatted = textwrap.indent(result.detail.strip(), prefix="    ")
            print(formatted)
        if status == "FAILED":
            failures += 1

    if failures:
        print(f"\nCompleted with {failures} failures.")
    else:
        print("\nAll steps passed (skipped steps indicate optional flows).")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
