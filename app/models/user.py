from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)  # stores normalized email or phone
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    # Relationships
    agents = relationship("Agent", back_populates="user")
    auth_tokens = relationship("AuthToken", back_populates="user")
    api_keys = relationship("ApiKey", back_populates="user")
