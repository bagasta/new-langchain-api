from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    sub: Optional[str] = None


class GoogleAuthRequest(BaseModel):
    email: Optional[str] = None
    tools: Optional[List[str]] = None


class GoogleAuthResponse(BaseModel):
    auth_required: bool = False
    auth_url: Optional[str] = None
    state: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)


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
