from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., description="Natural language query about cancer genomics data.", examples=["What genes are associated with lung cancer?"])


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Natural language answer from the agent.")
    provider: str = Field(..., description="Adapter used to generate the response (e.g. groq/llama-3, rule_based/deterministic).")
    tool_calls_made: list[str] = Field(default=[], description="Names of genomics tools invoked during the request.")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status.", examples=["ok"])
    provider: str = Field(..., description="Active agent adapter.")