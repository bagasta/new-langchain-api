from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str


class UserUpdate(UserBase):
    password: Optional[str] = None


class UserInDBBase(UserBase):
    id: str
    is_active: bool
    api_key: str
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class User(UserInDBBase):
    pass


class UserInDB(UserInDBBase):
    password_hash: str


# Agent slots schemas
class UserAgentSlotsResponse(BaseModel):
    """Response for getting user agent slot information"""
    total_slots: Optional[int] = Field(None, description="Total agent slots (null = unlimited)")
    used_slots: int = Field(..., description="Number of agents currently created")
    available_slots: Optional[int] = Field(None, description="Available slots (null = unlimited)")
    plan_code: str = Field(..., description="User's current plan")
    is_unlimited: bool = Field(..., description="Whether user has unlimited slots")


class UpdateAgentSlotsRequest(BaseModel):
    """Request to update user's agent slots"""
    agent_slots: Optional[int] = Field(None, ge=0, description="New slot count (null = unlimited, 0+ = limited)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_slots": 5
            }
        }

