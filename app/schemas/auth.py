from pydantic import BaseModel, validator
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum
from uuid import UUID


class PlanCode(str, Enum):
    PRO_M = "PRO_M"
    PRO_Y = "PRO_Y"
    TRIAL = "TRIAL"


class Token(BaseModel):
    jwt_token: str
    token_type: str


class TokenData(BaseModel):
    sub: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    email: Optional[str] = None
    tools: Optional[List[str]] = None
    scopes: Optional[List[str]] = None
    agent_id: Optional[UUID] = None


class GoogleAuthResponse(BaseModel):
    auth_required: bool
    auth_url: Optional[str] = None
    auth_state: Optional[str] = None
    required_scopes: Optional[List[str]] = None
    tokens: Optional[List[dict]] = None


class GoogleStatusRequest(BaseModel):
    tools: Optional[List[str]] = None
    scopes: Optional[List[str]] = None
    agent_id: Optional[UUID] = None


class RefreshStatusGoogleRequest(BaseModel):
    agent_id: UUID


class GoogleAuthCallback(BaseModel):
    code: str
    state: str


class AuthTokenCreate(BaseModel):
    service: str
    access_token: str
    refresh_token: Optional[str] = None
    scope: List[str]
    expires_at: Optional[datetime] = None


class AuthToken(BaseModel):
    id: str
    user_id: str
    service: str
    scope: List[str]
    expires_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApiKeyRequest(BaseModel):
    username: str
    password: str
    plan_code: PlanCode


class ApiKeyResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    plan_code: str


class TrialApiKeyRequest(BaseModel):
    ip_user: str


class TrialApiKeyResponse(ApiKeyResponse):
    user_id: UUID


class ApiKeyUpdateRequest(BaseModel):
    username: str
    password: str
    access_token: str
    plan_code: PlanCode


class UserPasswordUpdateRequest(BaseModel):
    user_id: UUID
    new_password: str
