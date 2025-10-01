from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Sequence
from uuid import uuid4
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from google.oauth2 import credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import requests
import json
import base64

from app.models import User, AuthToken
from app.schemas.auth import TokenData, AuthTokenCreate
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings
from app.core.logging import logger


def normalize_scopes(scopes: Sequence[str]) -> List[str]:
    """Return a deduplicated list of scopes in the order received."""
    seen = set()
    normalized = []
    for scope in scopes:
        if not scope:
            continue
        if scope not in seen:
            normalized.append(scope)
            seen.add(scope)
    return normalized


DEFAULT_GOOGLE_SCOPES: List[str] = normalize_scopes(
    [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.labels",
        "https://mail.google.com/",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/documents",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/gmail.addons.current.action.compose",
        "https://www.googleapis.com/auth/gmail.addons.current.message.action",
        "openid",
    ]
)

GOOGLE_TOOL_SCOPE_MAP: Dict[str, List[str]] = {
    "gmail": normalize_scopes(
        [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.compose",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/gmail.labels",
            "https://www.googleapis.com/auth/gmail.addons.current.action.compose",
            "https://www.googleapis.com/auth/gmail.addons.current.message.action",
            "https://mail.google.com/",
        ]
    ),
    "google_sheets": normalize_scopes(
        [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
    ),
    "google_calendar": normalize_scopes(
        [
            "https://www.googleapis.com/auth/calendar",
        ]
    ),
    "google_docs": normalize_scopes(
        [
            "https://www.googleapis.com/auth/documents",
        ]
    ),
    "google_drive": normalize_scopes(
        [
            "https://www.googleapis.com/auth/drive.file",
        ]
    ),
}

GOOGLE_PROFILE_SCOPES = normalize_scopes(
    [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]
)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        # expose settings so dependent components (e.g., tools) can access configuration
        self.settings = settings

    def get_google_tool_names(self) -> List[str]:
        return list(GOOGLE_TOOL_SCOPE_MAP.keys())

    def scopes_for_tools(self, tools: Sequence[str]) -> List[str]:
        """Return the minimal set of scopes required for the provided tools."""
        requested_scopes: List[str] = []
        for tool in tools:
            tool_scopes = GOOGLE_TOOL_SCOPE_MAP.get(tool)
            if tool_scopes:
                requested_scopes.extend(tool_scopes)

        if requested_scopes:
            # Always include basic profile scopes so we can identify the user
            requested_scopes.extend(GOOGLE_PROFILE_SCOPES)
            return normalize_scopes(requested_scopes)

        return DEFAULT_GOOGLE_SCOPES

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_user(self, email: str, password: str) -> User:
        hashed_password = get_password_hash(password)
        db_user = User(email=email, password_hash=hashed_password)
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def create_access_token(self, user_id: str) -> str:
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return create_access_token(
            subject=user_id, expires_delta=access_token_expires
        )

    def get_current_user(self, token: str) -> Optional[User]:
        token_data = self.verify_token(token)
        if token_data is None:
            return None
        user = self.db.query(User).filter(User.id == token_data.sub).first()
        return user

    def verify_token(self, token: str) -> Optional[TokenData]:
        from app.core.security import verify_token as verify_jwt_token

        user_id = verify_jwt_token(token)
        if user_id is None:
            return None
        return TokenData(sub=user_id)

    def create_google_auth_url(self, user_id: str, scopes: Optional[Sequence[str]] = None) -> Dict[str, str]:
        scopes = normalize_scopes(scopes or DEFAULT_GOOGLE_SCOPES)
        state_payload = {
            "u": user_id,
            "n": str(uuid4()),
            "s": scopes,
        }
        state_bytes = json.dumps(state_payload).encode("utf-8")
        state = base64.urlsafe_b64encode(state_bytes).decode("utf-8").rstrip("=")

        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
                }
            },
            scopes=scopes
        )

        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI

        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state
        )

        return {"auth_url": auth_url, "state": state}

    def exchange_google_code(
        self,
        code: str,
        state: str,
        scopes: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        try:
            if not scopes:
                scopes = DEFAULT_GOOGLE_SCOPES
            scopes = normalize_scopes(scopes)

            def _build_flow(scope_list: Sequence[str]) -> Flow:
                flow_instance = Flow.from_client_config(
                    {
                        "web": {
                            "client_id": settings.GOOGLE_CLIENT_ID,
                            "client_secret": settings.GOOGLE_CLIENT_SECRET,
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "redirect_uris": [settings.GOOGLE_REDIRECT_URI]
                        }
                    },
                    scopes=scope_list
                )
                flow_instance.redirect_uri = settings.GOOGLE_REDIRECT_URI
                return flow_instance

            # Try with original scopes first
            flow = _build_flow(scopes)

            try:
                flow.fetch_token(code=code)
            except ValueError as scope_err:
                message = str(scope_err)
                if "Scope has changed" not in message:
                    raise

                # Extract the actual scopes returned by Google
                parts = message.split(' to "')
                if len(parts) != 2 or not parts[1].endswith('".'):
                    raise

                scope_str = parts[1][:-2]
                actual_scopes = normalize_scopes(scope_str.split())

                if not actual_scopes:
                    raise

                # Create a new flow with the actual scopes returned by Google
                flow = _build_flow(actual_scopes)
                flow.fetch_token(code=code)

            if not flow.credentials:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch token from Google"
                )

            credentials = flow.credentials

            # Get user info from Google
            userinfo_service = build('oauth2', 'v2', credentials=credentials)
            user_info = userinfo_service.userinfo().get().execute()

            return {
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "scope": credentials.scopes,
                "expires_at": credentials.expiry,
                "email": user_info.get("email")
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google authentication failed: {str(e)}"
            )

    def save_auth_token(self, user_id: str, token_data: Dict[str, Any]) -> AuthToken:
        scope = token_data["scope"]
        if isinstance(scope, str):
            scope = normalize_scopes(scope.split())
        else:
            scope = normalize_scopes(scope)

        auth_token = self.db.query(AuthToken).filter(
            AuthToken.user_id == user_id,
            AuthToken.service == "google"
        ).first()

        new_refresh_token = token_data.get("refresh_token")

        if auth_token:
            auth_token.access_token = token_data["access_token"]
            if new_refresh_token:
                auth_token.refresh_token = new_refresh_token
            auth_token.scope = scope
            auth_token.expires_at = token_data.get("expires_at")
        else:
            auth_token = AuthToken(
                user_id=user_id,
                service="google",
                access_token=token_data["access_token"],
                refresh_token=new_refresh_token,
                scope=scope,
                expires_at=token_data.get("expires_at")
            )
            self.db.add(auth_token)

        self.db.commit()
        self.db.refresh(auth_token)
        return auth_token

    def get_user_auth_tokens(self, user_id: str) -> List[AuthToken]:
        return self.db.query(AuthToken).filter(AuthToken.user_id == user_id).all()

    def check_google_auth_scopes(self, user_id: str, required_scopes: List[str]) -> Dict[str, Any]:
        """
        Check if user's Google authentication covers the required scopes.
        Returns dict with:
        - has_auth: bool - whether user has Google auth
        - scopes_covered: bool - whether existing auth covers required scopes
        - missing_scopes: List[str] - scopes that are missing
        """
        tokens = self.get_user_auth_tokens(user_id)
        google_token = next((token for token in tokens if token.service == "google"), None)

        if not google_token:
            return {
                "has_auth": False,
                "scopes_covered": False,
                "missing_scopes": required_scopes
            }

        existing_scopes = set(google_token.scope or [])
        required_scopes_set = set(required_scopes)
        missing_scopes = list(required_scopes_set - existing_scopes)

        return {
            "has_auth": True,
            "scopes_covered": len(missing_scopes) == 0,
            "missing_scopes": missing_scopes
        }

    def revoke_google_auth(self, user_id: str) -> bool:
        """
        Revoke Google authentication for a user to allow re-authentication with different scopes.
        """
        try:
            google_token = self.db.query(AuthToken).filter(
                AuthToken.user_id == user_id,
                AuthToken.service == "google"
            ).first()

            if google_token:
                # Revoke the token with Google
                if google_token.access_token:
                    try:
                        requests.post(
                            "https://oauth2.googleapis.com/revoke",
                            params={"token": google_token.access_token}
                        )
                    except requests.RequestException:
                        # Ignore errors when revoking token
                        pass

                # Remove from database
                self.db.delete(google_token)
                self.db.commit()

            return True
        except Exception as e:
            logger.error("Failed to revoke Google auth", error=str(e), user_id=user_id)
            self.db.rollback()
            return False

    def refresh_google_token(self, user_id: str) -> Optional[AuthToken]:
        auth_token = self.db.query(AuthToken).filter(
            AuthToken.user_id == user_id,
            AuthToken.service == "google"
        ).first()

        if not auth_token or not auth_token.refresh_token:
            return None

        try:
            data = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "refresh_token": auth_token.refresh_token,
                "grant_type": "refresh_token"
            }

            response = requests.post("https://oauth2.googleapis.com/token", data=data)
            response.raise_for_status()

            token_data = response.json()

            auth_token.access_token = token_data["access_token"]
            auth_token.expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))

            self.db.commit()
            self.db.refresh(auth_token)
            return auth_token

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to refresh token: {str(e)}"
            )
