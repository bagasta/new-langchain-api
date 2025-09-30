from sqlalchemy import Column, String, Text, Enum, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
import enum
from app.models.base import Base


class ToolType(enum.Enum):
    BUILTIN = "builtin"
    CUSTOM = "custom"


class Tool(Base):
    __tablename__ = "tools"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text)
    schema = Column(JSONB, nullable=False)
    type = Column(Enum(ToolType), nullable=False)

    # Relationships
    agent_tools = relationship("AgentTool", back_populates="tool")


class AgentTool(Base):
    __tablename__ = "agent_tools"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True)
    tool_id = Column(UUID(as_uuid=True), ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True)
    config = Column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb")
    )

    # Relationships
    agent = relationship("Agent", back_populates="tools")
    tool = relationship("Tool", back_populates="agent_tools")
