from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, Sequence
from uuid import UUID
import base64
import json

from app.core.database import get_db
from app.core.deps import get_current_user, get_auth_service
from app.services.auth_service import (
    AuthService,
    DEFAULT_GOOGLE_SCOPES,
    normalize_scopes,
)
from app.models import User
from app.schemas.auth import Token, GoogleAuthRequest, GoogleAuthResponse, GoogleAuthCallback
from app.core.logging import logger

router = APIRouter()


@router.options("/{path:path}", include_in_schema=False)
async def auth_preflight(path: str) -> Response:
    """Handle CORS preflight requests for auth endpoints."""
    return Response(status_code=204)


@router.options("/", include_in_schema=False)
async def auth_preflight_root() -> Response:
    return Response(status_code=204)


@router.post("/login", response_model=Token)
async def login(
    email: str,
    password: str,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """User login endpoint"""
    try:
        user = auth_service.authenticate_user(email, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        access_token = auth_service.create_access_token(str(user.id))
        logger.info("User logged in successfully", user_id=str(user.id))

        return {"access_token": access_token, "token_type": "bearer"}

    except HTTPException as exc:
        logger.warning("Login failed", error=str(exc.detail), email=email)
        raise exc
    except Exception as e:
        logger.error("Login failed", error=str(e), email=email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )


@router.post("/register")
async def register(
    email: str,
    password: str,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """User registration endpoint"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        user = auth_service.create_user(email, password)
        access_token = auth_service.create_access_token(str(user.id))

        logger.info("User registered successfully", user_id=str(user.id))

        return {
            "message": "User registered successfully",
            "access_token": access_token,
            "token_type": "bearer"
        }

    except HTTPException as exc:
        logger.warning("Registration failed", error=str(exc.detail), email=email)
        raise exc
    except Exception as e:
        logger.error("Registration failed", error=str(e), email=email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


async def _init_google_auth(
    current_user: User,
    auth_service: AuthService,
    tools: Optional[Sequence[str]] = None,
):
    """Shared helper for initiating Google OAuth authentication."""
    try:
        # Prefer tool-specific scopes when provided, otherwise fall back to defaults
        scope_list = auth_service.scopes_for_tools(tools or [])

        scope_check = auth_service.check_google_auth_scopes(str(current_user.id), scope_list)

        if scope_check["has_auth"] and scope_check["scopes_covered"]:
            logger.info(
                "Google auth already covers required scopes",
                user_id=str(current_user.id),
            )
            return GoogleAuthResponse(
                auth_required=False,
                auth_url=None,
                state=None,
                scopes=scope_list,
            )

        if scope_check["has_auth"] and not scope_check["scopes_covered"]:
            logger.info(
                "Revoking existing Google auth to renew scopes",
                user_id=str(current_user.id),
                missing_scopes=scope_check["missing_scopes"],
            )
            auth_service.revoke_google_auth(str(current_user.id))

        auth_response = auth_service.create_google_auth_url(
            str(current_user.id), scope_list
        )

        logger.info("Google auth initiated", user_id=str(current_user.id))

        return GoogleAuthResponse(
            auth_required=True,
            auth_url=auth_response.get("auth_url"),
            state=auth_response.get("state"),
            scopes=scope_list,
        )

    except HTTPException as exc:
        logger.warning("Google auth initiation failed", error=str(exc.detail), user_id=str(current_user.id))
        raise exc
    except Exception as e:
        logger.error("Google auth initiation failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google auth: {str(e)}"
        )


@router.post("/google/auth", response_model=GoogleAuthResponse)
async def google_auth_post(
    request: GoogleAuthRequest,  # kept for backward compatibility
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Initiate Google OAuth authentication (POST)."""
    tools = request.tools or []
    return await _init_google_auth(current_user, auth_service, tools)


@router.get("/google/auth", response_model=GoogleAuthResponse)
async def google_auth_get(
    http_request: Request,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Initiate Google OAuth authentication (GET for clickable links)."""
    tools_param = http_request.query_params.get("tools")
    tools = [tool.strip() for tool in tools_param.split(",") if tool.strip()] if tools_param else None
    return await _init_google_auth(current_user, auth_service, tools)


async def process_google_callback(
    code: str,
    state: str,
    db: Session,
    auth_service: AuthService,
    scope: Optional[str] = None,
):
    """Process Google OAuth callback and persist user credentials."""
    try:
        state_data: Dict[str, Any] = {}
        if state:
            try:
                padded_state = state + "=" * (-len(state) % 4)
                decoded_state = base64.urlsafe_b64decode(padded_state.encode("utf-8")).decode("utf-8")
                state_data = json.loads(decoded_state)
            except Exception:
                logger.warning("Failed to decode Google OAuth state", state=state)

        # Use scopes from state first (most important - these are the ones originally requested)
        state_scopes = state_data.get("s") if state_data else None
        if state_scopes:
            scopes = normalize_scopes(state_scopes)
        elif scope:
            scopes = normalize_scopes(scope.split())
        else:
            scopes = DEFAULT_GOOGLE_SCOPES

        required_scopes = normalize_scopes(scopes)

        # Exchange code for tokens
        token_data = auth_service.exchange_google_code(code, state, required_scopes)

        user = None
        user_id_from_state = None
        state_user = state_data.get("u") if state_data else None
        if state_user:
            try:
                user_id_from_state = UUID(state_user)
                user = db.query(User).filter(User.id == user_id_from_state).first()
            except ValueError:
                logger.warning("Invalid user id in Google OAuth state", state=state)

        # Get or create user
        if not user:
            user = db.query(User).filter(User.email == token_data["email"]).first()
        if not user:
            # Create user with random password (they'll use Google OAuth)
            import secrets
            temp_password = secrets.token_urlsafe(32)
            user = auth_service.create_user(token_data["email"], temp_password)

        granted_scopes_raw = token_data.get("scope") or []
        if isinstance(granted_scopes_raw, str):
            granted_scopes = normalize_scopes(granted_scopes_raw.split())
        else:
            granted_scopes = normalize_scopes(granted_scopes_raw)

        missing_scopes = [scope for scope in required_scopes if scope not in granted_scopes]

        auth_required = False
        auth_url = None
        auth_state_resp = None

        if missing_scopes:
            logger.warning(
                "Google authentication incomplete",
                user_id=str(user.id),
                missing_scopes=missing_scopes,
            )
            auth_service.revoke_google_auth(str(user.id))
            auth_data = auth_service.create_google_auth_url(str(user.id), required_scopes)
            auth_required = True
            auth_url = auth_data.get("auth_url")
            auth_state_resp = auth_data.get("state")
        else:
            auth_service.save_auth_token(str(user.id), token_data)

        # Create access token for API authentication
        access_token = auth_service.create_access_token(str(user.id))

        logger.info(
            "Google OAuth callback processed",
            user_id=str(user.id),
            auth_required=auth_required,
            missing_scopes=missing_scopes,
        )

        message = (
            "Additional Google permissions are required. Please re-authenticate."
            if auth_required
            else "Google authentication successful"
        )

        return {
            "message": message,
            "access_token": access_token,
            "token_type": "bearer",
            "auth_required": auth_required,
            "auth_url": auth_url,
            "auth_state": auth_state_resp,
            "scopes": required_scopes,
            "granted_scopes": granted_scopes,
            "missing_scopes": missing_scopes,
        }

    except HTTPException as exc:
        logger.warning("Google OAuth callback failed", error=str(exc.detail))
        raise exc
    except Exception as e:
        logger.error("Google OAuth callback failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google authentication failed: {str(e)}"
        )


@router.get("/google/callback")
async def google_callback(
    code: str,
    state: str,
    scope: Optional[str] = None,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Handle Google OAuth callback"""
    return await process_google_callback(code, state, db, auth_service, scope)


@router.delete("/google/revoke")
async def revoke_google_auth(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Revoke Google authentication to allow re-authentication with different scopes"""
    try:
        success = auth_service.revoke_google_auth(str(current_user.id))
        if success:
            logger.info("Google auth revoked", user_id=str(current_user.id))
            return {"message": "Google authentication revoked successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to revoke Google authentication"
            )
    except HTTPException as exc:
        logger.warning("Google auth revocation failed", error=str(exc.detail), user_id=str(current_user.id))
        raise exc
    except Exception as e:
        logger.error("Google auth revocation failed", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke Google authentication: {str(e)}"
        )


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current user information"""
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at
    }


@router.get("/tokens")
async def get_user_tokens(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Get user's authentication tokens"""
    tokens = auth_service.get_user_auth_tokens(str(current_user.id))
    return {
        "tokens": [
            {
                "id": str(token.id),
                "service": token.service,
                "scope": token.scope,
                "expires_at": token.expires_at,
                "created_at": token.created_at
            }
            for token in tokens
        ]
    }
