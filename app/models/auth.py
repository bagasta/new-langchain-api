from sqlalchemy import Column, String, DateTime, ARRAY, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    service = Column(String(50), nullable=False)  # 'google', 'microsoft', etc.
    access_token = Column(String, nullable=False)
    refresh_token = Column(String)
    scope = Column(ARRAY(String), nullable=False)
    expires_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="auth_tokens")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    access_token = Column(String, nullable=False, unique=True)
    plan_code = Column(Enum('PRO_M', 'PRO_Y', 'TRIAL', name='plan_code_enum'), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    trial_ip = Column(String(45), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="api_keys")
