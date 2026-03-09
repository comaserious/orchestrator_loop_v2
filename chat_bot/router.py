from fastapi import APIRouter, HTTPException

from app_registry import app_register
from model import ChatRequest

router = app_register.register_router(APIRouter(prefix="/chat"))

@router.get("/")
async def root():
    return {"message" : "orchestrator loop chat bot service"}

@router.post("/api/v1")
async def chat(request: ChatRequest):
    try:
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))