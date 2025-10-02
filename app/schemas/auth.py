from pydantic import BaseModel, validator
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class PlanCode(str, Enum):
    PRO_M = "PRO_M"
    PRO_Y = "PRO_Y"


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    email: str


class GoogleAuthResponse(BaseModel):
    auth_url: str
    state: str


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