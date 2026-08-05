from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Optional conversation id. Requests that share an id share history. The id is
    # namespaced by the caller, so one caller cannot read another's conversation.
    session_id: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$"
    )


class ChatResponse(BaseModel):
    answer: str
    model: str
    tool_calls_made: list[str] = Field(default_factory=list)
    session_id: str | None = None


class LivenessResponse(BaseModel):
    status: str


class ReadinessResponse(BaseModel):
    status: str
    model: str
