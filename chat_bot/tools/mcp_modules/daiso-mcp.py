from chat_bot.tools.registry import register_tool

# https://github.com/hmmhmmhm/daiso-mcp

@register_tool(
    parameters={
        "server_url" : "https://mcp.aka.page",
        "require_approval" : "never",
    },
    tool_type="mcp"
)
def korea_store_mcp():
    """
    Use this MCP server — NOT web search — when the user's question is specifically about
    다이소, 올리브영, CU, 이마트24, 메가박스, 롯데시네마, or CGV.

    Supported capabilities:
    - 다이소: product search, store locator, inventory check, price lookup, in-store display location
    - 올리브영: nearby store search, product inventory check
    - CU: nearby store search, product inventory check
    - 이마트24: nearby store search, product search, inventory check
    - 메가박스: nearby theater search, now-showing movies, remaining seats by showtime
    - 롯데시네마: nearby theater search, now-showing movies, remaining seats by showtime
    - CGV: theater search by region, now-showing movies, full timetable

    Trigger examples:
    - "다이소에서 수납박스 재고 있어?"
    - "올리브영 강남 지점 주변 찾아줘"
    - "메가박스에서 오늘 아이언맨 몇 시에 해?"
    - "CGV 잔여 좌석 알려줘"
    """
    pass
