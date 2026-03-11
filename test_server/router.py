from fastapi import APIRouter
from app_registry import app_register
import os
import httpx

router = app_register.register_router(APIRouter(prefix="/test", tags=["test"]))

@router.get("/")
async def test():
    return {"message" : "test server rout"}

@router.get("/duckling")
async def duckling(query: str):
    try:
        DUCKLING_URL = os.getenv("DUCKLING_URL", "http://duckling:8000")

        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{DUCKLING_URL}/parse",
                data={   # ✅ form-urlencoded
                    "text": query,
                    "locale": "ko_KR",
                    "tz": "Asia/Seoul",
                    "dims": '["time"]'   # 중요: 문자열 JSON
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded"
                }
            )

            res.raise_for_status()

            data = res.json()
            print("-"*100)
            print(data)
            print("-"*100)

            return {"query" : query, "result" : data[0]["value"]["value"]}

    except Exception as e:
        return {"error" : str(e)}
    finally:
        await client.aclose()

