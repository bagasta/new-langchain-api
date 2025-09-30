from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    api_key = Column(String(128), unique=True, nullable=False, default=lambda: uuid.uuid4().hex)

    # Relationships
    agents = relationship("Agent", back_populates="user")
    auth_tokens = relationship("AuthToken", back_populates="user")
