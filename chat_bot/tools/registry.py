from typing import Callable

# function 툴: OpenAI에 schema로 전달 + 우리가 직접 실행
TOOLS: list[dict] = []
TOOL_MAP: dict[str, Callable] = {}

# MCP 툴: OpenAI에 서버 설정으로 전달 → 서버 측에서 자동 실행 (우리가 실행 불필요)
MCP_TOOLS: list[dict] = []


def register_tool(parameters: dict, tool_type: str = "function"):
    """
    tool_type="function" (기본): 일반 함수 툴 등록
    tool_type="mcp"            : MCP 서버 툴 등록
      parameters 예시:
        {"server_url": "https://...", "require_approval": "never"}
    """
    def decorator(func: Callable) -> Callable:
        if tool_type == "mcp":
            MCP_TOOLS.append({
                "type": "mcp",
                "server_label": func.__name__.replace("_", "-"),
                "server_url": parameters.get("server_url", ""),
                "require_approval": parameters.get("require_approval", "never"),
                "server_description": (func.__doc__ or "").strip(),
            })
        else:
            TOOLS.append({
                "type": "function",
                "name": func.__name__,
                "description": func.__doc__,
                "parameters": parameters,
            })
            TOOL_MAP[func.__name__] = func
        return func
    return decorator
