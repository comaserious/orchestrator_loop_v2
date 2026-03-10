from typing import Callable

TOOLS: list[dict] = []
TOOL_MAP: dict[str, Callable] = {}

def register_tool(parameters: dict):
    """
    Tool 함수에 붙이는 데코레이터.
    - TOOLS : OpenAI API에 전달할 스키마 목록
    - TOOL_MAP : 이름으로 실제 함수를 찾아 실행할 때 사용
    """
    def decorator(func: Callable) -> Callable:
        TOOLS.append({
            "type": "function",
            "name": func.__name__,
            "description": func.__doc__,
            "parameters": parameters,
        })
        TOOL_MAP[func.__name__] = func
        return func
    return decorator
