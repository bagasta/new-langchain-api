from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import verify_token
from app.models import User
from app.services.auth_service import AuthService
from app.services.agent_service import AgentService
from app.services.tool_service import ToolService
from app.services.execution_service import ExecutionService
from app.services.embedding_service import EmbeddingService

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    user_id = verify_token(token)

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Get auth service instance"""
    return AuthService(db)


def get_agent_service(db: Session = Depends(get_db)) -> AgentService:
    """Get agent service instance"""
    return AgentService(db)


def get_tool_service(db: Session = Depends(get_db)) -> ToolService:
    """Get tool service instance"""
    return ToolService(db)


def get_execution_service(db: Session = Depends(get_db)) -> ExecutionService:
    """Get execution service instance"""
    return ExecutionService(db)


def get_embedding_service(db: Session = Depends(get_db)) -> EmbeddingService:
    """Get embedding service instance"""
    return EmbeddingService(db)
