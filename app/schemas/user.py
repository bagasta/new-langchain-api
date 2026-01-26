from pydantic import BaseModel, Field
from typing import Optional

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
