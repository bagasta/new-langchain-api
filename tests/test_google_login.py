import pytest
from fastapi.testclient import TestClient
from app.core.config import settings

def test_google_login_endpoint(client: TestClient):
    """
    Test the public Google login endpoint.
    Verifies that it returns a valid auth URL and state without requiring authentication.
    """
    response = client.get(f"{settings.API_V1_STR}/auth/google/login")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["auth_required"] is True
    assert "auth_url" in data
    assert "auth_state" in data
    assert "required_scopes" in data
    
    # Verify auth_url contains expected parameters
    from urllib.parse import unquote
    auth_url = unquote(data["auth_url"])
    
    assert "accounts.google.com" in auth_url
    assert settings.GOOGLE_CLIENT_ID in auth_url
    assert settings.GOOGLE_REDIRECT_URI in auth_url
    
    # Verify state is present
    assert data["auth_state"] is not None
