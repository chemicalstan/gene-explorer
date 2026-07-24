from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from gene_explorer.agent import AgentRunError, run_agent
from gene_explorer.api.schemas import (
    ChatRequest,
    ChatResponse,
    LivenessResponse,
    ReadinessResponse,
)
from gene_explorer.config import Settings
from gene_explorer.repository import GeneRepository

logger = logging.getLogger(__name__)


def build_router(settings: Settings, agent: object, repo: GeneRepository) -> APIRouter:
    router = APIRouter(prefix="/v1")

    @router.post("/chat", response_model=ChatResponse, tags=["Agent"])
    async def chat(request: ChatRequest) -> ChatResponse:
        try:
            answer, tools = await run_agent(
                agent, repo, request.message, max_turns=settings.max_turns
            )
        except AgentRunError:
            logger.exception("agent run failed")
            raise HTTPException(status_code=502, detail="The model is unavailable.")
        return ChatResponse(answer=answer, model=settings.model, tool_calls_made=tools)

    @router.get("/health/live", response_model=LivenessResponse, tags=["System"])
    def live() -> LivenessResponse:
        return LivenessResponse(status="ok")

    @router.get("/health/ready", response_model=ReadinessResponse, tags=["System"])
    def ready() -> ReadinessResponse:
        return ReadinessResponse(status="ok", model=settings.model)

    return router
