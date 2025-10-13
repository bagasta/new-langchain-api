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

from app.models import User, AuthToken, ApiKey
from app.schemas.auth import TokenData, AuthTokenCreate, ApiKeyRequest, PlanCode
from app.core.security import create_access_token, verify_password, get_password_hash
from app.core.config import settings
from app.core.logging import logger
from datetime import datetime, timedelta


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


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        # expose settings so dependent components (e.g., tools) can access configuration
        self.settings = settings

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_user(self, email: str, password: str) -> User:
        hashed_password = get_password_hash(password)
        db_user = User(email=email, password_hash=hashed_password, created_at=datetime.utcnow())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def generate_api_key(self, email: str, password: str, plan_code: PlanCode) -> Dict[str, Any]:
        """Generate API key with plan-based expiration"""
        user = self.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )

        # Calculate expiration based on plan
        if plan_code == PlanCode.PRO_M:
            expires_at = datetime.utcnow() + timedelta(days=30)
        elif plan_code == PlanCode.PRO_Y:
            expires_at = datetime.utcnow() + timedelta(days=365)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan code"
            )

        # Create API key
        access_token = self.create_access_token(str(user.id))

        api_key = ApiKey(
            user_id=user.id,
            access_token=access_token,
            plan_code=plan_code.value,
            expires_at=expires_at,
            created_at=datetime.utcnow(),
            is_active=True
        )

        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_at": expires_at,
            "plan_code": plan_code.value
        }

    def get_user_api_keys(self, user_id: str) -> List[ApiKey]:
        """Get all API keys for a user"""
        return self.db.query(ApiKey).filter(ApiKey.user_id == user_id).all()

    def update_api_key(
        self,
        email: str,
        password: str,
        access_token: str,
        plan_code: PlanCode
    ) -> bool:
        """Update an existing API key's plan and expiration"""
        user = self.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )

        api_key = self.db.query(ApiKey).filter(
            ApiKey.access_token == access_token,
            ApiKey.user_id == user.id
        ).first()

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )

        if plan_code == PlanCode.PRO_M:
            expires_at = datetime.utcnow() + timedelta(days=30)
        elif plan_code == PlanCode.PRO_Y:
            expires_at = datetime.utcnow() + timedelta(days=365)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid plan code"
            )

        api_key.plan_code = plan_code.value
        api_key.expires_at = expires_at
        api_key.is_active = True

        self.db.commit()

        logger.info(
            "API key updated successfully",
            user_id=str(user.id),
            api_key_id=str(api_key.id),
            plan_code=plan_code.value
        )

        return True

    def deactivate_api_key(self, api_key_id: str, user_id: str) -> bool:
        """Deactivate an API key"""
        api_key = self.db.query(ApiKey).filter(
            ApiKey.id == api_key_id,
            ApiKey.user_id == user_id
        ).first()

        if api_key:
            api_key.is_active = False
            self.db.commit()
            return True
        return False

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
            requested_scopes = normalize_scopes(scopes or DEFAULT_GOOGLE_SCOPES)

            # Use manual token exchange to bypass Flow's scope validation
            token_data = self._manual_google_token_exchange(code, requested_scopes)

            # Create credentials object for API calls
            from google.oauth2.credentials import Credentials
            credentials = Credentials(
                token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                scopes=token_data["scope"]
            )

            # Get user info from Google
            userinfo_service = build('oauth2', 'v2', credentials=credentials)
            user_info = userinfo_service.userinfo().get().execute()

            # Validate that we have all requested scopes (Google may add extra ones)
            granted_scopes = set(token_data["scope"])
            required_scopes = set(requested_scopes)

            # Check if all required scopes are granted
            missing_scopes = required_scopes - granted_scopes
            if missing_scopes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Required scopes not granted: {', '.join(missing_scopes)}"
                )

            return {
                "access_token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "scope": token_data["scope"],
                "expires_at": token_data.get("expires_at"),
                "email": user_info.get("email")
            }

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Google authentication failed: {str(e)}"
            )

    def _manual_google_token_exchange(self, code: str, scopes: List[str]) -> Dict[str, Any]:
        """Manually exchange Google OAuth code for token, bypassing Flow's scope validation."""
        import requests
        from datetime import datetime, timedelta

        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI
        }

        response = requests.post("https://oauth2.googleapis.com/token", data=data)
        response.raise_for_status()

        token_data = response.json()

        # Calculate expiry time
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # Handle scopes - Google may return different scopes than requested
        returned_scopes = token_data.get("scope", "")
        if isinstance(returned_scopes, str):
            returned_scopes = normalize_scopes(returned_scopes.split())
        else:
            returned_scopes = normalize_scopes(returned_scopes)

        # Ensure we have at least our required scopes
        required_scopes = set(scopes)
        granted_scopes = set(returned_scopes)

        missing_scopes = required_scopes - granted_scopes
        if missing_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Required scopes not granted: {', '.join(missing_scopes)}"
            )

        return {
            "access_token": token_data["access_token"],
            "refresh_token": token_data.get("refresh_token"),
            "scope": returned_scopes,
            "expires_at": expires_at
        }

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

            # Update the access token and expiry
            auth_token.access_token = token_data["access_token"]
            auth_token.expires_at = datetime.utcnow() + timedelta(seconds=token_data.get("expires_in", 3600))

            # Handle scope changes if returned
            if "scope" in token_data:
                new_scopes = normalize_scopes(token_data["scope"].split())
                current_scopes = auth_token.scope or []

                # Merge scopes - keep all current scopes and add new ones
                merged_scopes = normalize_scopes(list(set(current_scopes + new_scopes)))
                auth_token.scope = merged_scopes

            self.db.commit()
            self.db.refresh(auth_token)
            return auth_token

        except Exception as e:
            # Handle scope change errors gracefully
            if "Scope has changed" in str(e) or "invalid_scope" in str(e):
                # Try to continue with existing token if it's still valid
                if auth_token.expires_at and auth_token.expires_at > datetime.utcnow():
                    logger.warning("Scope changed during refresh, using existing token", user_id=user_id)
                    return auth_token

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to refresh token: {str(e)}"
            )
