from pydantic import BaseModel
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    provider: str
    tool_calls_made: list[str] = []


class ChatResponse(BaseModel):
    answer: str
    provider: str
    tool_calls_made: list[str] = []