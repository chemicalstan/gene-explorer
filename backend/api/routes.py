import logging
import os

from backend.api.schemas import ChatRequest, ChatResponse, HealthResponse
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.agent.agent import Agent

logger = logging.getLogger(__name__)


def create_app(agent: Agent) -> FastAPI:
    app = FastAPI(
        title="Gene Explorer API",
        description="Conversational agent for querying cancer genomics data via the Open Targets Platform.",
        version="1.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.post(
        "/chat",
        response_model=ChatResponse,
        summary="Chat with the genomics agent",
        tags=["Agent"],
    )
    async def chat(request: ChatRequest) -> ChatResponse:
        """Send a natural language query; the agent calls the relevant genomics tool and returns an answer."""
        try:
            answer, tool_calls = agent.run(request.message)
            return ChatResponse(
                answer=answer,
                provider=agent.provider_name,
                tool_calls_made=tool_calls,
            )
        except Exception as exc:
            logger.exception("Unhandled error in /chat: %s", exc)
            raise HTTPException(
                status_code=500,
                detail="An internal error occurred. Please try again.",
            )

    @app.get(
        "/health",
        response_model=HealthResponse,
        summary="Health check",
        tags=["System"],
    )
    def health() -> HealthResponse:
        """Returns service liveness and the active agent adapter."""
        return HealthResponse(status="ok", provider=agent.provider_name)

    return app
