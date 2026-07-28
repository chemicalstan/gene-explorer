# NOTE: no `from __future__ import annotations` here. slowapi wraps the chat
# endpoint, and FastAPI must resolve the real body-model annotation through that
# wrapper. String annotations resolve against slowapi's module and fail, which
# makes FastAPI treat the request body as a query parameter.
from agents import Agent
from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter

from gene_explorer.agent import AgentRunError, run_agent
from gene_explorer.api.schemas import (
    ChatRequest,
    ChatResponse,
    LivenessResponse,
    ReadinessResponse,
)
from gene_explorer.auth import build_api_key_dependency
from gene_explorer.config import Settings
from gene_explorer.domain import ToolCallLog
from gene_explorer.logging_config import get_logger

logger = get_logger("gene_explorer.chat")


def build_router(settings: Settings, agent: Agent[ToolCallLog], limiter: Limiter) -> APIRouter:
    router = APIRouter(prefix="/v1")
    require_api_key = build_api_key_dependency(settings)

    @router.post("/chat", response_model=ChatResponse, tags=["Agent"])
    @limiter.limit(settings.rate_limit)
    async def chat(
        request: Request,
        body: ChatRequest,
        _: None = Depends(require_api_key),
    ) -> ChatResponse:
        try:
            result = await run_agent(agent, body.message, max_turns=settings.max_turns)
        except AgentRunError as exc:
            logger.exception("agent_run_failed")
            raise HTTPException(status_code=502, detail="The model is unavailable.") from exc

        usage = result.usage
        # Log usage and cost, but NOT the message content (it may contain PII).
        logger.info(
            "chat_completed",
            model=settings.model,
            tool_calls=result.tool_calls,
            message_length=len(body.message),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.total_tokens,
            llm_requests=usage.requests,
            estimated_cost_usd=round(
                usage.cost_usd(settings.input_price_per_1m, settings.output_price_per_1m),
                6,
            ),
        )
        return ChatResponse(
            answer=result.answer,
            model=settings.model,
            tool_calls_made=result.tool_calls,
        )

    @router.get("/health/live", response_model=LivenessResponse, tags=["System"])
    def live() -> LivenessResponse:
        return LivenessResponse(status="ok")

    @router.get("/health/ready", response_model=ReadinessResponse, tags=["System"])
    def ready() -> ReadinessResponse:
        return ReadinessResponse(status="ok", model=settings.model)

    return router
