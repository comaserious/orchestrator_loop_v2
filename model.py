from pydantic import BaseModel

class ChatRequest(BaseModel):
    model_name: str
    message: str