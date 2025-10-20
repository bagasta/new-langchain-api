from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, delete

from app.models import AgentUpload, Embedding
from app.core.logging import logger


class UploadService:
    def __init__(self, db: Session):
        self.db = db

    def list_uploads(
        self,
        agent_id: UUID,
        user_id: UUID,
    ) -> List[AgentUpload]:
        stmt = (
            select(AgentUpload)
            .where(AgentUpload.agent_id == agent_id, AgentUpload.user_id == user_id)
            .order_by(AgentUpload.created_at.desc())
        )
        uploads = self.db.execute(stmt).scalars().all()
        return uploads

    def get_upload(
        self,
        upload_id: UUID,
        agent_id: UUID,
        user_id: UUID,
    ) -> Optional[AgentUpload]:
        stmt = (
            select(AgentUpload)
            .where(
                AgentUpload.id == upload_id,
                AgentUpload.agent_id == agent_id,
                AgentUpload.user_id == user_id,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def delete_upload(
        self,
        upload: AgentUpload,
    ) -> AgentUpload:
        logger.info(
            "Deleting agent upload",
            upload_id=str(upload.id),
            agent_id=str(upload.agent_id),
            chunk_count=upload.chunk_count,
        )

        # Remove associated embeddings
        if upload.embedding_ids:
            stmt = (
                delete(Embedding)
                .where(Embedding.id.in_(upload.embedding_ids))
            )
            self.db.execute(stmt)
        else:
            stmt = delete(Embedding).where(Embedding.upload_id == upload.id)
            self.db.execute(stmt)

        self.db.delete(upload)
        self.db.commit()
        return upload
