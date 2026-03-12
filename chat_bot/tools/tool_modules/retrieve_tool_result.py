from chat_bot.tools.registry import register_tool
from redis.asyncio import Redis

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
def retrieve_tool_result(tool_id: str) -> str:
    """
    Use this tool to retrieve the result of a tool.
    """
    try:
        pass
    except Exception as e:
        return f"Error in retrieve_tool_result: {e}"

async def save_tool_result(tool_id: str, result: dict) -> None:
    try:
        pass
    except Exception as e:
        return f"Error in save_tool_result: {e}"