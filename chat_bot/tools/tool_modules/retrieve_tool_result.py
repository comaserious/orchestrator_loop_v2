from chat_bot.tools.registry import register_tool
from redis_manager import RedisManager
import json

TOOL_RESULT_KEY_PREFIX = "tool_result:"

@register_tool(
    parameters={
        "type": "object",
        "properties": {
            "tool_id": {
                "type": "string",
                "description": "The ID of the tool to retrieve the result from.",
            },
        },
        "required": ["tool_id"],
    }
)
async def retrieve_tool_result(tool_id: str) -> str:
    """
    Use this tool to retrieve the result of a tool.
    """
    try:
        key = f"{TOOL_RESULT_KEY_PREFIX}{tool_id}"

        redis_client = RedisManager.get_client()
    
        return await redis_client.hgetall(key)
    except Exception as e:
        return f"Error in retrieve_tool_result: {e}"

async def save_tool_result(tool_id: str, result: dict | list) -> None:
    """result는 dict 또는 list. Redis에 JSON 문자열로 저장함."""
    redis_client = RedisManager.get_client()
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call RedisManager.init() at startup.")

    key = f"{TOOL_RESULT_KEY_PREFIX}{tool_id}"
    pipe = redis_client.pipeline()
    pipe.hset(
        key,
        mapping={"result": json.dumps(result, ensure_ascii=False, default=str)},
    )
    pipe.expire(key, 60 * 60)
    await pipe.execute()