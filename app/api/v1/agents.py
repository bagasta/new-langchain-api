from fastapi import APIRouter, Depends, HTTPException, Response, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.deps import (
    get_api_key_user,
    get_agent_service,
    get_execution_service,
    get_auth_service,
    get_embedding_service,
    get_tool_service,
    get_upload_service,
)
from app.services.agent_service import AgentService
from app.services.execution_service import ExecutionService
from app.services.embedding_service import EmbeddingService
from app.services.auth_service import AuthService, DEFAULT_GOOGLE_SCOPES
from app.services.tool_service import ToolService
from app.services.upload_service import UploadService
from app.models import User, ExecutionStatus
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentCreateResponse,
    AgentUploadRecord,
    AgentUploadListResponse,
)
from app.core.logging import logger

router = APIRouter()


@router.post("/", response_model=AgentCreateResponse)
async def create_agent(
    agent_data: AgentCreate,
    current_user: User = Depends(get_api_key_user),
    agent_service: AgentService = Depends(get_agent_service),
    tool_service: ToolService = Depends(get_tool_service),
    auth_service: AuthService = Depends(get_auth_service)
):
    """Create a new agent"""
    try:
        agent = agent_service.create_agent(current_user.id, agent_data)
        logger.info("Agent created", agent_id=str(agent.id), user_id=str(current_user.id))

        selected_tools = agent_data.tools or []
        required_scopes = tool_service.get_required_scopes(selected_tools)
        requires_google_auth = bool(required_scopes)

        auth_required = False
        auth_url = None
        auth_state = None

        if requires_google_auth:
            tokens = auth_service.get_user_auth_tokens(str(current_user.id))
            required_scope_set = set(required_scopes)
            has_google = False
            for token in tokens:
                if token.service != "google":
                    continue
                token_scopes = set(token.scope or [])
                if required_scope_set.issubset(token_scopes):
                    has_google = True
                    break

            if not has_google:
                auth_data = auth_service.create_google_auth_url(
                    str(current_user.id), required_scopes or DEFAULT_GOOGLE_SCOPES
                )
                auth_required = True
                auth_url = auth_data.get("auth_url")
                auth_state = auth_data.get("state")

        agent_response = AgentCreateResponse.model_validate(agent, from_attributes=True)
        agent_response = agent_response.model_copy(
            update={
                "auth_required": auth_required,
                "auth_url": auth_url,
                "auth_state": auth_state,
            }
        )

        return agent_response
    except Exception as e:
        logger.error("Failed to create agent", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create agent: {str(e)}"
        )


@router.get("/", response_model=List[AgentResponse])
@router.get("", response_model=List[AgentResponse], include_in_schema=False)
async def get_user_agents(
    current_user: User = Depends(get_api_key_user),
    agent_service: AgentService = Depends(get_agent_service)
):
    """Get all agents for the current user"""
    agents = agent_service.get_user_agents(current_user.id)
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    current_user: User = Depends(get_api_key_user),
    agent_service: AgentService = Depends(get_agent_service)
):
    """Get a specific agent"""
    agent = agent_service.get_agent(agent_id, current_user.id)
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    current_user: User = Depends(get_api_key_user),
    agent_service: AgentService = Depends(get_agent_service)
):
    """Update an agent"""
    try:
        agent = agent_service.update_agent(agent_id, current_user.id, agent_data)
        logger.info("Agent updated", agent_id=str(agent_id), user_id=str(current_user.id))
        return agent
    except Exception as e:
        logger.error("Failed to update agent", error=str(e), agent_id=str(agent_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent: {str(e)}"
        )


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: UUID,
    current_user: User = Depends(get_api_key_user),
    agent_service: AgentService = Depends(get_agent_service)
):
    """Delete an agent"""
    try:
        agent_service.delete_agent(agent_id, current_user.id)
        logger.info("Agent deleted", agent_id=str(agent_id), user_id=str(current_user.id))
        return {"message": "Agent deleted successfully"}
    except Exception as e:
        logger.error("Failed to delete agent", error=str(e), agent_id=str(agent_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete agent: {str(e)}"
        )


@router.post("/{agent_id}/documents")
async def upload_agent_document(
    agent_id: UUID,
    file: UploadFile = File(...),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    batch_size: Optional[int] = Form(None),
    current_user: User = Depends(get_api_key_user),
    agent_service: AgentService = Depends(get_agent_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
):
    """Upload a document, convert it to clean text, and store vector embeddings."""
    try:
        agent = agent_service.get_agent(agent_id, current_user.id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to load agent for document ingestion", error=str(exc), agent_id=str(agent_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to prepare agent: {exc}"
        )

    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "text/plain",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Upload pdf, docx, pptx, or txt files.",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        result = await embedding_service.ingest_file(
            agent,
            file.filename,
            file.content_type,
            file_bytes,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            batch_size=batch_size,
            uploaded_by=current_user.id,
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc)
        )
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Failed to ingest document",
            error=str(exc),
            agent_id=str(agent_id),
            filename=file.filename,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest document: {exc}"
        )

    logger.info(
        "Document ingested",
        agent_id=str(agent_id),
        filename=file.filename,
        chunks=result.get("chunks"),
    )

    return {
        "message": "Document processed and embeddings stored.",
        "chunks": result.get("chunks"),
        "embedding_ids": result.get("embedding_ids"),
        "upload_id": result.get("upload_id"),
    }


@router.get("/{agent_id}/documents", response_model=AgentUploadListResponse)
async def list_agent_documents(
    agent_id: UUID,
    current_user: User = Depends(get_api_key_user),
    agent_service: AgentService = Depends(get_agent_service),
    upload_service: UploadService = Depends(get_upload_service),
):
    """List uploaded documents for an agent."""
    agent_service.get_agent(agent_id, current_user.id)
    uploads = upload_service.list_uploads(agent_id, current_user.id)
    return AgentUploadListResponse(
        uploads=[
            AgentUploadRecord.model_validate(upload, from_attributes=True)
            for upload in uploads
        ]
    )


@router.delete(
    "/{agent_id}/documents/{upload_id}",
    response_model=AgentUploadRecord,
    status_code=status.HTTP_200_OK,
)
async def delete_agent_document(
    agent_id: UUID,
    upload_id: UUID,
    current_user: User = Depends(get_api_key_user),
    agent_service: AgentService = Depends(get_agent_service),
    upload_service: UploadService = Depends(get_upload_service),
):
    """Delete previously uploaded document and associated embeddings."""
    agent_service.get_agent(agent_id, current_user.id)

    upload = upload_service.get_upload(upload_id, agent_id, current_user.id)
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )

    upload_record = AgentUploadRecord.model_validate(upload, from_attributes=True)
    upload_record = upload_record.model_copy(
        update={
            "is_deleted": True,
            "deleted_at": datetime.now(timezone.utc),
        }
    )

    upload_service.delete_upload(upload)
    return upload_record


@router.post("/{agent_id}/execute", response_model=AgentExecuteResponse)
async def execute_agent(
    agent_id: UUID,
    execute_data: AgentExecuteRequest,
    current_user: User = Depends(get_api_key_user),
    execution_service: ExecutionService = Depends(get_execution_service)
):
    """Execute an agent"""
    try:
        execution = await execution_service.execute_agent(
            agent_id,
            current_user.id,
            execute_data.input,
            execute_data.parameters,
            execute_data.session_id
        )

        if execution.status == ExecutionStatus.FAILED:
            error_detail = None
            if isinstance(execution.output, dict):
                error_detail = execution.output.get("error")
            error_detail = error_detail or execution.error_message or "Agent execution failed"
            logger.error(
                "Agent execution failed",
                agent_id=str(agent_id),
                execution_id=str(execution.id),
                error=error_detail
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_detail
            )

        logger.info("Agent executed", agent_id=str(agent_id), execution_id=str(execution.id))
        response_text = None
        if isinstance(execution.output, dict):
            response_text = execution.output.get("output")
        elif isinstance(execution.output, str):
            response_text = execution.output

        return AgentExecuteResponse(
            execution_id=str(execution.id),
            status=execution.status.value,
            message="Agent execution started",
            response=response_text,
            session_id=execution.session_id
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to execute agent", error=str(e), agent_id=str(agent_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute agent: {str(e)}"
        )


@router.get("/{agent_id}/executions")
async def get_agent_executions(
    agent_id: UUID,
    current_user: User = Depends(get_api_key_user),
    execution_service: ExecutionService = Depends(get_execution_service)
):
    """Get execution history for an agent"""
    executions = execution_service.get_agent_executions(agent_id, current_user.id)
    return {
        "executions": [
            {
                "id": str(exec.id),
                "input": exec.input,
                "output": exec.output,
                "status": exec.status.value,
                "duration_ms": exec.duration_ms,
                "error_message": exec.error_message,
                "created_at": exec.created_at
            }
            for exec in executions
        ]
    }


@router.get("/executions/stats")
async def get_execution_stats(
    current_user: User = Depends(get_api_key_user),
    execution_service: ExecutionService = Depends(get_execution_service)
):
    """Get execution statistics"""
    stats = execution_service.get_execution_stats(current_user.id)
    return stats
