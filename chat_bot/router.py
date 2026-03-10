from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app_registry import app_register
from chat_bot.responses.generator_v1 import generator_v1
from model import ChatRequest

router = app_register.register_router(APIRouter(prefix="/chat"))

@router.get("/")
async def root():
    return {"message" : "orchestrator loop chat bot service"}


import chat_bot.tools.tool_modules  # noqa: F401 - 자동 등록 트리거
from chat_bot.tools.registry import TOOLS, TOOL_MAP

@router.post("/api/v1")
async def chat(request: ChatRequest):

    try:
        response = StreamingResponse(
            generator_v1(request),
            media_type = "text/event-stream",
            headers = {
                "Content-Type" : "text/event-stream",
                "Cache-Control" : "no-cache",
                "Connection" : "keep-alive"
            } 
        )

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))