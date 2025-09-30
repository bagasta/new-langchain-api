from fastapi import APIRouter, Response
from .auth import router as auth_router
from .agents import router as agents_router
from .tools import router as tools_router

api_router = APIRouter()


@api_router.options("/{path:path}", include_in_schema=False)
async def v1_preflight(path: str) -> Response:
    from app.core.logging import logger

    logger.info("V1 preflight", path=path)
    return Response(status_code=204)

api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(agents_router, prefix="/agents", tags=["agents"])
api_router.include_router(tools_router, prefix="/tools", tags=["tools"])
