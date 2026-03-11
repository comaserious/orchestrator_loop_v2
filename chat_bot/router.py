from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app_registry import app_register
from chat_bot.responses.generator_v1 import generator_v1, resume_generator
from model import ChatRequest, ResumeRequest

router = app_register.register_router(APIRouter(prefix="/chat", tags=["chat"]))

_SSE_HEADERS = {
    "Content-Type":  "text/event-stream",
    "Cache-Control": "no-cache",
    "Connection":    "keep-alive",
}


@router.get("/")
async def root():
    return {"message": "orchestrator loop chat bot service"}


import chat_bot.tools.tool_modules  # noqa: F401 - 자동 등록 트리거
from chat_bot.tools.registry import TOOLS, TOOL_MAP


@router.post("/api/v1")
async def chat(request: ChatRequest):
    try:
        return StreamingResponse(
            generator_v1(request),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/v1/resume")
async def chat_resume(request: ResumeRequest):
    """HIL 사용자 선택 후 오케스트레이터를 재개하는 엔드포인트."""
    try:
        return StreamingResponse(
            resume_generator(request.session_id, request.choice),
            media_type="text/event-stream",
            headers=_SSE_HEADERS,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
