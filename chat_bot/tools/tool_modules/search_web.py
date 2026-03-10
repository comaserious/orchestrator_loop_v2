from chat_bot.tools.registry import register_tool
from tavily import TavilyClient

import logging

logger = logging.getLogger(__name__)

# https://docs.tavily.com/documentation/api-reference/endpoint/search#body-topic

@register_tool(
    parameters={
        "type" : "object",
        "properties" : {
            "query" : {
                "type" : "string",
                "description" : "The query to search the web for.",
            }
        },
        "required" : ["query"],
    }
)
def search_web(query: str) -> list[dict]:
    """
    Use this tool when the user asks for current or real-time information.
    It generates an optimized search query based on the user's question and retrieves relevant results from the web.
    """
    try:
        tavily_client = TavilyClient()
        response = tavily_client.search(
            query = query   
        )

        return response['results']
        
    except Exception as e:
        logger.error(f"Error in search_web: {e}")
        raise e