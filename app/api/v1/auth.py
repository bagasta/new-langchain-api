from fastapi import APIRouter, Depends, HTTPException, Response, Query, Body, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional, List, Union
from uuid import UUID
import base64
import json

from app.core.database import get_db
from app.core.deps import (
    get_current_user,
    get_api_key_user,
    get_agent_service,
    get_auth_service,
    get_tool_service,
    security,
)
from app.services.auth_service import (
    AuthService,
    DEFAULT_GOOGLE_SCOPES,
    normalize_scopes,
)
from app.models import User, ApiKey
from app.schemas.auth import (
    Token,
    GoogleAuthRequest,
    GoogleAuthResponse,
    GoogleStatusRequest,
    GoogleAuthCallback,
    ApiKeyRequest,
    ApiKeyResponse,
    TrialApiKeyRequest,
    TrialApiKeyResponse,
    ApiKeyUpdateRequest,
    UserPasswordUpdateRequest,
    RefreshStatusGoogleRequest,
)
from app.services.tool_service import ToolService
from app.services.agent_service import AgentService
from app.core.logging import logger

router = APIRouter()





@router.post("/login", response_model=Token)
async def login(
    password: str = Query(..., description="User password (plaintext)"),
    email: Optional[str] = Query(
        None, description="Email address. Optional if phone or identifier is provided."
    ),
    phone: Optional[str] = Query(
        None,
        description="Phone number (digits with optional leading +). Optional if email or identifier is provided.",
    ),
    identifier: Optional[str] = Query(
        None, description="Email or phone value. Overrides email/phone if supplied."
    ),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """User login endpoint"""
    try:
        contact = identifier or email or phone
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide an email address or phone number."
            )

        user = await auth_service.authenticate_user(contact, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user"
            )

        jwt_token = auth_service.create_access_token(str(user.id))
        logger.info("User logged in successfully", user_id=str(user.id))

        return {"jwt_token": jwt_token, "token_type": "bearer"}

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
    password: str = Query(..., description="User password (plaintext)"),
    email: Optional[str] = Query(
        None, description="Email address. Optional if phone or identifier is provided."
    ),
    phone: Optional[str] = Query(
        None,
        description="Phone number (digits with optional leading +). Optional if email or identifier is provided.",
    ),
    identifier: Optional[str] = Query(
        None, description="Email or phone value. Overrides email/phone if supplied."
    ),
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """User registration endpoint"""
    try:
        contact = identifier or email or phone
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide an email address or phone number."
            )

        user = await auth_service.create_user(contact, password)

        logger.info("User registered successfully", user_id=str(user.id))

        return {
            "message": "User registered successfully",
            "user_id": str(user.id),
            "email": user.email
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
    tool_service: ToolService,
    tools: Optional[str] = None,
    scopes: Optional[str] = None,
    agent_id: Optional[str] = None,
    request: Optional[Union[GoogleStatusRequest, GoogleAuthRequest]] = None,
):
    """Shared helper for initiating Google OAuth authentication."""
    try:
        required_scopes = _resolve_required_scopes(
            tools, scopes, request, tool_service
        )

        auth_response = auth_service.create_google_auth_url(
            str(current_user.id),
            required_scopes,
            agent_id=agent_id,
        )

        logger.info("Google auth initiated", user_id=str(current_user.id))

        return {**auth_response, "required_scopes": required_scopes}

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
    tools: Optional[str] = Query(
        None,
        description="Comma-separated tool names to derive required Google scopes.",
    ),
    scopes: Optional[str] = Query(
        None,
        description="Space- or comma-separated scopes to request explicitly.",
    ),
    agent_id: Optional[str] = Query(
        None,
        description="Agent ID to scope the OAuth grant to a specific agent.",
    ),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    tool_service: ToolService = Depends(get_tool_service),
):
    """Initiate Google OAuth authentication (POST)."""
    return await _init_google_auth(
        current_user,
        auth_service,
        tool_service,
        tools,
        scopes,
        agent_id or (str(request.agent_id) if request and request.agent_id else None),
        request,
    )
    return await _init_google_auth(
        current_user,
        auth_service,
        tool_service,
        tools,
        scopes,
        agent_id or (str(request.agent_id) if request and request.agent_id else None),
        request,
    )


@router.get("/google/login", response_model=GoogleAuthResponse)
async def google_login(
    tools: Optional[str] = Query(
        None,
        description="Comma-separated tool names to derive required Google scopes.",
    ),
    scopes: Optional[str] = Query(
        None,
        description="Space- or comma-separated scopes to request explicitly.",
    ),
    auth_service: AuthService = Depends(get_auth_service),
    tool_service: ToolService = Depends(get_tool_service),
):
    """Initiate Google OAuth login (public endpoint)."""
    required_scopes = _resolve_required_scopes(tools, scopes, None, tool_service)
    
    auth_data = auth_service.create_google_auth_url(
        user_id=None,
        scopes=required_scopes,
    )

    return {
        "auth_required": True,
        "auth_url": auth_data.get("auth_url"),
        "auth_state": auth_data.get("state"),
        "required_scopes": required_scopes,
        "tokens": [],
    }
async def google_auth_get(
    tools: Optional[str] = Query(
        None,
        description="Comma-separated tool names to derive required Google scopes.",
    ),
    scopes: Optional[str] = Query(
        None,
        description="Space- or comma-separated scopes to request explicitly.",
    ),
    agent_id: Optional[str] = Query(
        None,
        description="Agent ID to scope the OAuth grant to a specific agent.",
    ),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    tool_service: ToolService = Depends(get_tool_service),
):
    """Initiate Google OAuth authentication (GET for clickable links)."""
    return await _init_google_auth(
        current_user,
        auth_service,
        tool_service,
        tools,
        scopes,
        agent_id,
        None,
    )


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

        scopes = DEFAULT_GOOGLE_SCOPES
        state_scopes = state_data.get("s") if state_data else None
        if state_scopes:
            scopes = normalize_scopes(state_scopes)
        elif scope:
            scopes = normalize_scopes(scope.split())

        # Exchange code for tokens
        token_data = auth_service.exchange_google_code(code, state, scopes)
        print(f"DEBUG: Token data received. Email: {token_data.get('email')}")

        user = None
        user_id_from_state = None
        state_user = state_data.get("u") if state_data else None
        state_agent = state_data.get("a") if state_data else None
        if state_user:
            try:
                user_id_from_state = UUID(state_user)
                user = db.query(User).filter(User.id == user_id_from_state).first()
            except ValueError:
                logger.warning("Invalid user id in Google OAuth state", state=state)

        # Get or create user
        # Get or create user
        if not user:
            print(f"DEBUG: Searching user by email: {token_data['email']}")
            user = db.query(User).filter(User.email == token_data["email"]).first()
        
        if not user:
            print(f"DEBUG: User not found, creating new user for {token_data['email']}")
            # Create user with random password (they'll use Google OAuth)
            import secrets
            temp_password = secrets.token_urlsafe(32)
            user = await auth_service.create_user(token_data["email"], temp_password)
            
            # Auto-activate user since Google verified the email
            user.is_active = True
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"DEBUG: User created and activated with ID: {user.id}")
        else:
            print(f"DEBUG: User found with ID: {user.id}")
            # Auto-activate existing user if they login via Google (verifies email)
            if not user.is_active:
                user.is_active = True
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"DEBUG: User activated via Google login")

        # Save auth token
        # Save auth token
        auth_service.save_auth_token(str(user.id), token_data, state_agent)

        # Ensure user has an API key (Plan) and get the access token
        api_key = auth_service.ensure_api_key_for_user(user.id)

        logger.info("Google OAuth callback processed", user_id=str(user.id))

        # Redirect to frontend with token
        # Use FRONTEND_URL from env or default to localhost
        import os
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        redirect_url = f"{frontend_url}/auth/callback?token={api_key.access_token}"
        return RedirectResponse(url=redirect_url)

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


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user information"""
    plan_code: Optional[str] = None
    token = credentials.credentials

    api_key = (
        db.query(ApiKey)
        .filter(
            ApiKey.access_token == token,
            ApiKey.user_id == current_user.id,
            ApiKey.is_active.is_(True),
        )
        .first()
    )

    if not api_key:
        api_key = (
            db.query(ApiKey)
            .filter(
                ApiKey.user_id == current_user.id,
                ApiKey.is_active.is_(True),
            )
            .order_by(ApiKey.expires_at.desc())
            .first()
        )

    display_token = token

    if api_key:
        plan_code = api_key.plan_code
        display_token = api_key.access_token

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "access_token": display_token,
        "plan_code": plan_code,
    }


@router.post("/api-key", response_model=ApiKeyResponse)
async def generate_api_key(
    request: ApiKeyRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Generate API key with plan-based expiration"""
    try:
        api_key_data = await auth_service.generate_api_key(
            identifier=request.username,
            password=request.password,
            plan_code=request.plan_code
        )

        logger.info("API key generated successfully", user_id=api_key_data.get("user_id"), plan_code=request.plan_code)

        return ApiKeyResponse(**api_key_data)

    except HTTPException as exc:
        logger.warning("API key generation failed", error=str(exc.detail), username=request.username)
        raise exc
    except Exception as e:
        logger.error("API key generation failed", error=str(e), username=request.username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate API key: {str(e)}"
        )


@router.post("/api-key/trial", response_model=TrialApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def generate_trial_api_key(
    request: TrialApiKeyRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Issue a trial API key for visitors based on their IP address."""
    try:
        api_key_data = auth_service.create_trial_api_key(request.ip_user)

        logger.info(
            "Trial API key issued",
            trial_ip=request.ip_user,
            user_id=str(api_key_data.get("user_id")),
        )

        return TrialApiKeyResponse(**api_key_data)
    except HTTPException as exc:
        logger.warning(
            "Trial API key issuance failed",
            error=str(exc.detail),
            trial_ip=request.ip_user,
        )
        raise exc
    except Exception as e:
        logger.error(
            "Trial API key issuance failed",
            error=str(e),
            trial_ip=request.ip_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate trial API key: {str(e)}"
        )


@router.post("/api-key/update", response_model=bool)
async def update_api_key(
    request: ApiKeyUpdateRequest,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update an existing API key by extending its expiration"""
    try:
        result = await auth_service.update_api_key(
            identifier=request.username,
            password=request.password,
            access_token=request.access_token,
            plan_code=request.plan_code
        )

        logger.info(
            "API key update endpoint completed successfully",
            email=request.username,
            plan_code=request.plan_code.value
        )

        return result

    except HTTPException as exc:
        logger.warning(
            "API key update failed",
            error=str(exc.detail),
            username=request.username
        )
        raise exc
    except Exception as e:
        logger.error(
            "API key update failed",
            error=str(e),
            username=request.username
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update API key: {str(e)}"
        )


@router.post("/user/update-password", response_model=bool)
async def update_user_password(
    request: UserPasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Update the authenticated user's password"""
    if current_user.id != request.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update another user's password"
        )

    try:
        result = auth_service.update_user_password(request.user_id, request.new_password)

        logger.info("User password updated", user_id=str(request.user_id))
        return result

    except HTTPException as exc:
        logger.warning(
            "User password update failed",
            error=str(exc.detail),
            user_id=str(request.user_id)
        )
        raise exc
    except Exception as e:
        logger.error(
            "User password update failed",
            error=str(e),
            user_id=str(request.user_id)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user password: {str(e)}"
        )


@router.post("/activate")
async def activate_user(
    email: str,
    db: Session = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Activate a user account"""
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        if user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already active"
            )

        # Activate the user
        user.is_active = True
        db.commit()
        db.refresh(user)

        logger.info("User activated successfully", user_id=str(user.id))

        return {
            "message": "User activated successfully",
            "user_id": str(user.id),
            "email": user.email,
            "is_active": user.is_active
        }

    except HTTPException as exc:
        logger.warning("User activation failed", error=str(exc.detail), email=email)
        raise exc
    except Exception as e:
        logger.error("User activation failed", error=str(e), email=email)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Activation failed: {str(e)}"
        )


def _parse_scope_query(raw_scopes: Optional[str]) -> List[str]:
    """Split and normalise scopes provided as a query string."""
    if not raw_scopes:
        return []
    parts = [
        part.strip()
        for part in raw_scopes.replace(",", " ").split()
        if part.strip()
    ]
    return normalize_scopes(parts)


def _resolve_required_scopes(
    tools_query: Optional[str],
    scopes_query: Optional[str],
    request: Optional[Union[GoogleStatusRequest, GoogleAuthRequest]],
    tool_service: ToolService,
) -> List[str]:
    body_scopes = (
        normalize_scopes(request.scopes) if request and request.scopes else []
    )
    if body_scopes:
        return body_scopes

    query_scopes = _parse_scope_query(scopes_query)
    if query_scopes:
        return query_scopes

    body_tools = request.tools if request and request.tools else []
    tools = body_tools
    if not tools and tools_query:
        tools = [tool.strip() for tool in tools_query.split(",") if tool.strip()]

    if tools:
        scoped = tool_service.get_required_scopes(tools)
        if scoped:
            return scoped

    return DEFAULT_GOOGLE_SCOPES


def _build_google_tokens_response(
    required_scopes: List[str],
    current_user: User,
    auth_service: AuthService,
    agent_id: Optional[str] = None,
):
    tokens = auth_service.get_user_auth_tokens(str(current_user.id), agent_id)
    required_scope_set = set(required_scopes)

    if agent_id:
        candidate_tokens = [
            token
            for token in tokens
            if token.service == "google"
            and str(getattr(token, "agent_id", None)) == agent_id
        ]
        tokens = candidate_tokens
    else:
        candidate_tokens = [token for token in tokens if token.service == "google"]

    has_required_scopes = any(
        required_scope_set.issubset(set(token.scope or []))
        for token in candidate_tokens
    )

    token_payload = [
        {
            "id": str(token.id),
            "service": token.service,
            "scope": token.scope,
            "expires_at": token.expires_at,
            "created_at": token.created_at,
        }
        for token in tokens
    ]

    if not required_scopes:
        return {
            "auth_required": False,
            "auth_url": None,
            "auth_state": None,
            "required_scopes": required_scopes,
            "tokens": token_payload,
        }

    if has_required_scopes:
        return {
            "auth_required": False,
            "auth_url": None,
            "auth_state": None,
            "required_scopes": required_scopes,
            "tokens": token_payload,
        }

    auth_data = auth_service.create_google_auth_url(
        str(current_user.id), required_scopes, agent_id=agent_id
    )

    return {
        "auth_required": True,
        "auth_url": auth_data.get("auth_url"),
        "auth_state": auth_data.get("state"),
        "required_scopes": required_scopes,
        "tokens": token_payload,
    }


@router.get("/google")
async def get_google_tokens(
    tools: Optional[str] = Query(
        None,
        description="Comma-separated tool names to derive required Google scopes.",
    ),
    scopes: Optional[str] = Query(
        None,
        description="Space- or comma-separated scopes to request explicitly.",
    ),
    agent_id: Optional[str] = Query(
        None,
        description="Agent ID to scope the OAuth grant to a specific agent.",
    ),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    tool_service: ToolService = Depends(get_tool_service),
):
    """Return Google auth status, initiating OAuth when scopes are missing."""
    required_scopes = _resolve_required_scopes(tools, scopes, None, tool_service)
    return _build_google_tokens_response(
        required_scopes, current_user, auth_service, agent_id
    )


@router.post("/google")
async def get_google_tokens_post(
    request: Optional[GoogleStatusRequest] = None,
    tools: Optional[str] = Query(
        None,
        description="Comma-separated tool names to derive required Google scopes.",
    ),
    scopes: Optional[str] = Query(
        None,
        description="Space- or comma-separated scopes to request explicitly.",
    ),
    agent_id: Optional[str] = Query(
        None,
        description="Agent ID to scope the OAuth grant to a specific agent.",
    ),
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    tool_service: ToolService = Depends(get_tool_service),
):
    """Return Google auth status using request body (tools/scopes) when provided."""
    required_scopes = _resolve_required_scopes(
        tools, scopes, request, tool_service
    )
    resolved_agent_id = (
        str(request.agent_id) if request and request.agent_id else agent_id
    )
    return _build_google_tokens_response(
        required_scopes, current_user, auth_service, resolved_agent_id
    )


@router.post("/refresh-status-google")
async def refresh_google_auth_status(
    request: RefreshStatusGoogleRequest = Body(
        ...,
        description="Agent ID to check Google authentication status for.",
    ),
    current_user: User = Depends(get_api_key_user),
    auth_service: AuthService = Depends(get_auth_service),
    agent_service: AgentService = Depends(get_agent_service),
    tool_service: ToolService = Depends(get_tool_service),
):
    """Refresh and return Google auth status for a specific agent using API key auth."""
    try:
        agent_id = request.agent_id
        agent = agent_service.get_agent(agent_id, current_user.id)
        agent_tools = agent_service.get_agent_tools(agent_id, current_user.id)
        tool_names = [tool.name for tool in agent_tools if tool.name]
        required_scopes = tool_service.get_required_scopes(tool_names)

        refreshed = False
        refreshed_token = None
        try:
            refreshed_token = auth_service.refresh_google_token(
                str(current_user.id),
                str(agent_id),
            )
            if not refreshed_token:
                refreshed_token = auth_service.refresh_google_token(
                    str(current_user.id),
                    None,
                )
            refreshed = refreshed_token is not None
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(
                "Failed to refresh Google token",
                error=str(exc),
                agent_id=str(agent_id),
                user_id=str(current_user.id),
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to refresh Google authentication status",
            ) from exc

        tokens_agent = auth_service.get_user_auth_tokens(
            str(current_user.id), str(agent_id)
        )
        tokens_global = auth_service.get_user_auth_tokens(str(current_user.id), None)
        required_scope_set = set(required_scopes)

        combined_tokens = [
            token
            for token in (tokens_agent + tokens_global)
            if getattr(token, "service", None) == "google"
        ]
        granted_scopes = set()
        for token in combined_tokens:
            for scope in token.scope or []:
                granted_scopes.add(scope)

        has_any_google_token = bool(combined_tokens)
        missing_scopes = (
            sorted(required_scope_set - granted_scopes) if required_scope_set else []
        )

        status_text = (
            "Authenticated"
            if (has_any_google_token or not required_scope_set)
            else "Unauthenticated"
        )

        return {
            "agent_id": str(agent.id),
            "status": status_text,
            "refreshed": refreshed,
            "required_scopes": required_scopes,
            "granted_scopes": sorted(granted_scopes),
            "missing_scopes": missing_scopes,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "Failed to fetch Google auth status",
            error=str(exc),
            agent_id=str(agent_id),
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch Google authentication status",
        ) from exc
