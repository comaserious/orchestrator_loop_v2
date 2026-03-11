from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from dotenv import load_dotenv

    # router 로드
    from chat_bot.router import router as chat_bot_router
    from test_server.router import router as test_router
    
    from app_registry import app_register

    load_dotenv()
    
    # router 등록
    app_register.include_routers(app)

    

    yield
    print("Shutting down...")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}