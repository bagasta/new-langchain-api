from datetime import datetime, timedelta

from app.services import auth_service as auth_module
from app.services.auth_service import AuthService, normalize_scopes


def test_exchange_google_code_handles_scope_expansion(monkeypatch):
    service = AuthService(db=None)  # type: ignore[arg-type]

    attempts = {"count": 0}
    flow_scopes = []

    class DummyCredentials:
        def __init__(self, scopes):
            self.token = "access-token"
            self.refresh_token = "refresh-token"
            self.scopes = scopes
            self.expiry = datetime.utcnow() + timedelta(hours=1)

    class DummyFlow:
        def __init__(self, scopes):
            self.scopes = scopes
            self.credentials = None
            self.redirect_uri = None

        def fetch_token(self, code):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise ValueError('Scope has changed from "scopeA scopeB" to "scopeA scopeB scopeC".')
            self.credentials = DummyCredentials(list(self.scopes))

    def fake_from_client_config(config, scopes):
        flow_scopes.append(tuple(scopes))
        return DummyFlow(tuple(scopes))

    class DummyGet:
        def execute(self):
            return {"email": "user@example.com"}

    class DummyUserInfo:
        def get(self):
            return DummyGet()

    class DummyService:
        def userinfo(self):
            return DummyUserInfo()

    monkeypatch.setattr(auth_module.Flow, "from_client_config", staticmethod(fake_from_client_config))
    monkeypatch.setattr(auth_module, "build", lambda *args, **kwargs: DummyService())

    token_data = service.exchange_google_code("code", "state", scopes=["scopeA", "scopeB"])

    assert attempts["count"] == 2
    assert normalize_scopes(["scopeA", "scopeB"]) == list(flow_scopes[0])
    assert normalize_scopes(["scopeA", "scopeB", "scopeC"]) == list(flow_scopes[1])
    assert token_data["scope"] == ["scopeA", "scopeB", "scopeC"]
