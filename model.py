from pydantic import BaseModel


class ChatRequest(BaseModel):
    model_name: str
    message: str


class ResumeRequest(BaseModel):
    session_id: str
    choice: str