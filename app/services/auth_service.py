import base64
import json
import re
import requests
import secrets
from datetime import datetime, timedelta
from ipaddress import ip_address
from typing import Optional, List, Dict, Any, Sequence
from uuid import UUID, uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from google.oauth2 import credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.models import User, AuthToken, ApiKey
from app.schemas.auth import TokenData, AuthTokenCreate, PlanCode
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

GOOGLE_IDENTITY_SCOPES: List[str] = normalize_scopes(
    [
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
        "openid",
    ]
)


class AuthService:
    _EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    _PHONE_REGEX = re.compile(r"^\d{8,15}$")

    @staticmethod
    def _is_supported_hash(password: str) -> bool:
        if not password:
            return False
        if password.startswith("$2b$12$") and len(password) == 60:
            return True
        if password.startswith("$bcrypt-sha256$"):
            return True
        return False

    @classmethod
    def _normalize_identifier(cls, raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None

        candidate = raw.strip()
        if not candidate:
            return None

        if cls._EMAIL_REGEX.match(candidate):
            return candidate.lower()

        digits_only = re.sub(r"\D", "", candidate)
        if digits_only and cls._PHONE_REGEX.match(digits_only):
            return digits_only
        return None

    def __init__(self, db: Session):
        self.db = db
        # expose settings so dependent components (e.g., tools) can access configuration
        self.settings = settings

    def _get_user_by_normalized_identifier(self, normalized_identifier: str) -> Optional[User]:
        query = self.db.query(User)
        if "@" in normalized_identifier:
            return query.filter(func.lower(User.email) == normalized_identifier).first()
        return query.filter(User.email == normalized_identifier).first()

    def _get_user_by_identifier(self, identifier: str) -> Optional[User]:
        normalized = self._normalize_identifier(identifier)
        if not normalized:
            return None
        return self._get_user_by_normalized_identifier(normalized)

    def authenticate_user(self, identifier: str, password: str) -> Optional[User]:
        user = self._get_user_by_identifier(identifier)
        if not user:
            return None
        if password == user.password_hash:
            return user
        if verify_password(password, user.password_hash):
            return user
        return None

    def create_user(self, identifier: str, password: str) -> User:
        normalized = self._normalize_identifier(identifier)
        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide a valid email address or phone number.",
            )

        existing_user = self._get_user_by_normalized_identifier(normalized)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account already exists for this email address or phone number.",
            )

        hashed_password = get_password_hash(password)
        db_user = User(email=normalized, password_hash=hashed_password, created_at=datetime.utcnow())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user

    def generate_api_key(self, identifier: str, password: str, plan_code: PlanCode) -> Dict[str, Any]:
        """Generate API key with plan-based expiration"""
        user = self.authenticate_user(identifier, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
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

    def _purge_expired_trial_api_keys(self, reference_time: Optional[datetime] = None) -> None:
        """Remove expired trial API keys."""
        if reference_time is None:
            reference_time = datetime.utcnow()

        expired_keys = (
            self.db.query(ApiKey)
            .filter(
                ApiKey.plan_code == PlanCode.TRIAL.value,
                ApiKey.expires_at < reference_time,
            )
            .all()
        )

        if not expired_keys:
            return

        for api_key in expired_keys:
            api_key.is_active = False
            self.db.delete(api_key)

        self.db.commit()
        logger.info("Purged expired trial API keys", count=len(expired_keys))

    def create_trial_api_key(self, raw_ip: str) -> Dict[str, Any]:
        """Create or reuse a trial API key for the provided IP address."""
        try:
            validated_ip = ip_address(raw_ip)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid IP address format.",
            ) from None

        now = datetime.utcnow()
        ip_str = str(validated_ip)

        # Remove any expired trial keys before issuing a new one
        self._purge_expired_trial_api_keys(now)

        # If an active trial key already exists for this IP, return it
        existing_key = (
            self.db.query(ApiKey)
            .filter(
                ApiKey.trial_ip == ip_str,
                ApiKey.plan_code == PlanCode.TRIAL.value,
                ApiKey.is_active == True,  # noqa: E712 - SQLAlchemy comparison
                ApiKey.expires_at > now,
            )
            .order_by(ApiKey.created_at.desc())
            .first()
        )

        if existing_key:
            logger.info(
                "Reusing existing trial API key",
                api_key_id=str(existing_key.id),
                trial_ip=ip_str,
            )
            return {
                "access_token": existing_key.access_token,
                "token_type": "bearer",
                "expires_at": existing_key.expires_at,
                "plan_code": existing_key.plan_code,
                "user_id": existing_key.user_id,
            }

        trial_email = f"trial_{uuid4().hex}@trial.local"
        random_password = secrets.token_urlsafe(32)
        hashed_password = get_password_hash(random_password)

        trial_user = User(
            email=trial_email,
            password_hash=hashed_password,
            is_active=True,
            created_at=now,
        )
        self.db.add(trial_user)
        self.db.flush()  # ensure trial_user.id is populated

        expires_at = now + timedelta(days=14)
        access_token = create_access_token(
            str(trial_user.id),
            expires_delta=timedelta(days=14),
        )

        api_key = ApiKey(
            user_id=trial_user.id,
            access_token=access_token,
            plan_code=PlanCode.TRIAL.value,
            expires_at=expires_at,
            created_at=now,
            is_active=True,
            trial_ip=ip_str,
        )

        self.db.add(api_key)
        self.db.commit()
        self.db.refresh(api_key)

        logger.info(
            "Issued new trial API key",
            api_key_id=str(api_key.id),
            trial_ip=ip_str,
            user_id=str(trial_user.id),
        )

        return {
            "access_token": api_key.access_token,
            "token_type": "bearer",
            "expires_at": api_key.expires_at,
            "plan_code": api_key.plan_code,
            "user_id": trial_user.id,
        }

    def get_user_api_keys(self, user_id: str) -> List[ApiKey]:
        """Get all API keys for a user"""
        return self.db.query(ApiKey).filter(ApiKey.user_id == user_id).all()

    def update_user_password(self, user_id: UUID, new_password: str) -> bool:
        """Update a user's password with plaintext or pre-hashed input."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if self._is_supported_hash(new_password):
            user.password_hash = new_password
        else:
            user.password_hash = get_password_hash(new_password)

        self.db.commit()
        logger.info("User password updated successfully", user_id=str(user.id))
        return True

    def update_api_key(
        self,
        identifier: str,
        password: str,
        access_token: str,
        plan_code: PlanCode
    ) -> bool:
        """Update an existing API key's plan and expiration"""
        user = self.authenticate_user(identifier, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
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
        requested_scopes = normalize_scopes(scopes or DEFAULT_GOOGLE_SCOPES)
        scopes = normalize_scopes(list(requested_scopes) + GOOGLE_IDENTITY_SCOPES)
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
            requested_scopes = normalize_scopes(list(requested_scopes) + GOOGLE_IDENTITY_SCOPES)

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
