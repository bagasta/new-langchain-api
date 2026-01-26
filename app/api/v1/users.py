from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_api_key_user
from app.models import User, Agent
from app.schemas.user import UserAgentSlotsResponse, UpdateAgentSlotsRequest
from app.models.auth import ApiKey
from app.core.logging import logger

router = APIRouter()


@router.get("/me/agent-slots", response_model=UserAgentSlotsResponse)
async def get_my_agent_slots(
    current_user: User = Depends(get_api_key_user),
    db: Session = Depends(get_db)
):
    """Get current user's agent slot information"""
    # Count user's agents
    used_slots = db.query(Agent).filter(Agent.user_id == current_user.id).count()
    
    # Get user's plan
    api_key = (
        db.query(ApiKey)
        .filter(
            ApiKey.user_id == current_user.id,
            ApiKey.is_active == True,
            ApiKey.agent_id.is_(None)
        )
        .order_by(ApiKey.created_at.desc())
        .first()
    )
    
    plan_code = api_key.plan_code if api_key else "UNKNOWN"
    
    # Calculate availability
    is_unlimited = current_user.agent_slots is None
    available_slots = None if is_unlimited else max(0, current_user.agent_slots - used_slots)
    
    return UserAgentSlotsResponse(
        total_slots=current_user.agent_slots,
        used_slots=used_slots,
        available_slots=available_slots,
        plan_code=plan_code,
        is_unlimited=is_unlimited
    )


@router.patch("/{user_id}/agent-slots", response_model=UserAgentSlotsResponse)
async def update_user_agent_slots(
    user_id: UUID,
    request: UpdateAgentSlotsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_api_key_user)
):
    """
    Update a user's agent slots (accessible via n8n or admin).
    
    - Set agent_slots to null for unlimited
    - Set agent_slots to integer (0+) for limited slots
    """
    # Find target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update slots
    target_user.agent_slots = request.agent_slots
    db.commit()
    db.refresh(target_user)
    
    logger.info(
        "Agent slots updated",
        user_id=str(user_id),
        new_slots=request.agent_slots,
        updated_by=str(current_user.id)
    )
    
    # Count user's agents
    used_slots = db.query(Agent).filter(Agent.user_id == target_user.id).count()
    
    # Get user's plan
    api_key = (
        db.query(ApiKey)
        .filter(
            ApiKey.user_id == target_user.id,
            ApiKey.is_active == True,
            ApiKey.agent_id.is_(None)
        )
        .order_by(ApiKey.created_at.desc())
        .first()
    )
    
    plan_code = api_key.plan_code if api_key else "UNKNOWN"
    
    # Calculate availability
    is_unlimited = target_user.agent_slots is None
    available_slots = None if is_unlimited else max(0, target_user.agent_slots - used_slots)
    
    return UserAgentSlotsResponse(
        total_slots=target_user.agent_slots,
        used_slots=used_slots,
        available_slots=available_slots,
        plan_code=plan_code,
        is_unlimited=is_unlimited
    )
