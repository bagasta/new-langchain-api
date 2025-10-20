from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Boolean,
    Integer,
    BigInteger,
    DateTime,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.models.base import Base


class AgentUpload(Base):
    __tablename__ = "agent_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    filename = Column(String(512), nullable=False)
    content_type = Column(String(255), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    chunk_count = Column(Integer, nullable=False)
    embedding_ids = Column(
        ARRAY(UUID(as_uuid=True)),
        nullable=False,
        server_default=text("'{}'::uuid[]"),
        default=list,
    )
    details = Column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
        default=dict,
    )
    is_deleted = Column(
        Boolean,
        nullable=False,
        server_default=text("false"),
        default=False,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="uploads")
    user = relationship("User", back_populates="uploads")
    embeddings = relationship(
        "Embedding",
        back_populates="upload",
        passive_deletes=True,
    )

    def mark_deleted(self) -> None:
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)
