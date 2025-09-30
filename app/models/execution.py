from sqlalchemy import Column, String, Integer, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from app.models.base import Base


class ExecutionStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Execution(Base):
    __tablename__ = "executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    input = Column(JSONB)
    output = Column(JSONB)
    session_id = Column(String(255), index=True)
    status = Column(Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    duration_ms = Column(Integer)
    error_message = Column(String)

    # Relationships
    agent = relationship("Agent", back_populates="executions", passive_deletes=True)
