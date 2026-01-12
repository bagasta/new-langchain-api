from sqlalchemy import Column, String, Enum, ForeignKey, BigInteger, DateTime, text
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
    
    # Token limiting fields
    token_limit = Column(BigInteger, nullable=True, comment="Maximum tokens allowed for this agent")
    tokens_used = Column(BigInteger, nullable=False, server_default=text("0"), default=0, comment="Total tokens used by this agent")
    token_reset_date = Column(DateTime(timezone=True), nullable=True, comment="Optional date for periodic token reset")

    # Relationships
    user = relationship("User", back_populates="agents")
    tools = relationship("AgentTool", back_populates="agent", passive_deletes=True)
    executions = relationship("Execution", back_populates="agent", passive_deletes=True)
    embeddings = relationship("Embedding", back_populates="agent", passive_deletes=True)
    uploads = relationship("AgentUpload", back_populates="agent", passive_deletes=True)
    auth_tokens = relationship("AuthToken", back_populates="agent", passive_deletes=True)
    api_keys = relationship("ApiKey", back_populates="agent", passive_deletes=True)
    system_message_history = relationship("AgentSystemMessageHistory", back_populates="agent", passive_deletes=True)
