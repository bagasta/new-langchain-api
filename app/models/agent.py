from sqlalchemy import Column, String, Enum, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
import uuid
import enum
from app.models.base import Base


class AgentStatus(enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DELETED = "deleted"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    config = Column(JSONB, nullable=False)
    status = Column(Enum(AgentStatus), default=AgentStatus.ACTIVE)
    mcp_servers = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        default=dict,
    )
    allowed_tools = Column(
        ARRAY(String),
        nullable=False,
        server_default=text("'{}'::text[]"),
        default=list,
    )

    # Relationships
    user = relationship("User", back_populates="agents")
    tools = relationship("AgentTool", back_populates="agent", passive_deletes=True)
    executions = relationship("Execution", back_populates="agent", passive_deletes=True)
    embeddings = relationship("Embedding", back_populates="agent")
