from sqlalchemy import Column, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import relationship
import uuid
from app.models.base import Base


class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536), nullable=False)  # OpenAI embedding size
    metadata_json = Column("metadata", JSONB)
    upload_id = Column(
        UUID(as_uuid=True),
        ForeignKey("agent_uploads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    agent = relationship("Agent", back_populates="embeddings")
    upload = relationship("AgentUpload", back_populates="embeddings")
