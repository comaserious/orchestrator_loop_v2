import asyncio
import json
import logging

from openai import AsyncOpenAI

import chat_bot.tools.tool_modules  # noqa: F401 - function 툴 자동 등록
import chat_bot.tools.mcp_modules   # noqa: F401 - MCP 툴 자동 등록
from chat_bot.tools.registry import TOOLS, MCP_TOOLS, TOOL_MAP
from chat_bot.responses.prompts import SYSTEM_PROMPT_BASE, build_web_search_system_prompt
from model import ChatRequest

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10
MAX_TOOL_OUTPUT_CHARS = 20_000


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _execute_tool(name: str, args: dict) -> tuple[str, object]:
    """
    function 툴을 실행. MCP 툴은 OpenAI 서버 측에서 처리되므로 여기서 실행하지 않음.
    """
    fn = TOOL_MAP.get(name)
    if fn is None:
        raise ValueError(f"등록되지 않은 툴: '{name}'")

    if asyncio.iscoroutinefunction(fn):
        raw = await fn(**args)
    else:
        raw = await asyncio.to_thread(fn, **args)

    if isinstance(raw, (dict, list)):
        serialized = json.dumps(raw, ensure_ascii=False)
    else:
        serialized = str(raw)

    return serialized[:MAX_TOOL_OUTPUT_CHARS], raw


async def generator_v1(request: ChatRequest):
    try:
        client = AsyncOpenAI()

        input_messages = [
            {"role": "system", "content": SYSTEM_PROMPT_BASE},
            {"role": "user",   "content": request.message},
        ]

        total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        for iteration in range(MAX_TOOL_ITERATIONS):
            # function_call : 우리가 직접 실행해야 하는 툴
            function_calls_in_turn = []
            # MCP 툴 패널을 이미 열었는지 여부 (tools.start 중복 방지)
            tools_panel_opened = False

            # ── 1단계: LLM 스트리밍 ───────────────────────────────────────────
            async for event in await client.responses.create(
                model="gpt-4.1",
                input=input_messages,
                tools=TOOLS + MCP_TOOLS,   # function 툴 + MCP 툴 모두 전달
                stream=True,
                # parallel_tool_calls=True,
            ):
                yield f"data: {event.model_dump_json()}\n\n"

                # 토큰 누적
                if event.type == "response.completed":
                    usage = getattr(event.response, "usage", None)
                    if usage:
                        total_usage["input_tokens"]  += getattr(usage, "input_tokens",  0)
                        total_usage["output_tokens"] += getattr(usage, "output_tokens", 0)
                        total_usage["total_tokens"]  += getattr(usage, "total_tokens",  0)

                # ── MCP 툴 호출 시작 (서버 측 실행 → 우리는 UI 상태만 관리) ──
                elif event.type == "response.output_item.added":
                    item = event.item
                    if getattr(item, "type", None) == "mcp_call":
                        if not tools_panel_opened:
                            yield _sse({"type": "tools.start", "tools": [item.name]})
                            tools_panel_opened = True
                        yield _sse({
                            "type": "tool.executing",
                            "name": item.name,
                            "args": {"server": item.server_label},
                        })

                # ── MCP 툴 호출 완료 / function_call 수집 ────────────────────
                elif event.type == "response.output_item.done":
                    item = event.item
                    if getattr(item, "type", None) == "mcp_call":
                        if item.error:
                            yield _sse({"type": "tool.error", "name": item.name, "error": item.error})
                        else:
                            yield _sse({"type": "tool.done", "name": item.name})
                    elif getattr(item, "type", None) == "function_call":
                        function_calls_in_turn.append(item)

            # ── 2단계: function_call 없으면 최종 응답 (MCP는 이미 처리됨) ───
            if not function_calls_in_turn:
                yield _sse({"type": "usage.final", "usage": total_usage, "iterations": iteration + 1})
                yield _sse({"type": "stream.done", "iterations": iteration + 1})
                yield "data: [DONE]\n\n"
                return

            # ── 3단계: function_call 실행 ─────────────────────────────────────
            if not tools_panel_opened:
                yield _sse({"type": "tools.start", "tools": [c.name for c in function_calls_in_turn]})
                tools_panel_opened = True

            search_results_accumulated: list[dict] = []
            tool_results = []

            for call in function_calls_in_turn:
                func_args = json.loads(call.arguments)
                yield _sse({"type": "tool.executing", "name": call.name, "args": func_args})

                try:
                    serialized, raw = await _execute_tool(call.name, func_args)

                    if call.name == "search_web" and isinstance(raw, list):
                        search_results_accumulated.extend(raw)

                    yield _sse({"type": "tool.done", "name": call.name})

                except Exception as e:
                    serialized = f"[오류] {call.name} 실행 실패: {e}"
                    logger.error(serialized)
                    yield _sse({"type": "tool.error", "name": call.name, "error": str(e)})

                tool_results.append({
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": serialized,
                })

            # ── 4단계: 검색 결과가 있으면 RAG 프롬프트 교체 ─────────────────
            if search_results_accumulated:
                input_messages[0] = {
                    "role": "system",
                    "content": build_web_search_system_prompt(search_results_accumulated),
                }
                citations = [
                    {"index": i, "title": item.get("title", ""), "url": item.get("url", "")}
                    for i, item in enumerate(search_results_accumulated, start=1)
                ]
                yield _sse({"type": "citations.ready", "citations": citations})

            # ── 5단계: context 확장 후 다음 LLM 호출 ────────────────────────
            for call in function_calls_in_turn:
                input_messages.append({
                    "type": "function_call",
                    "id": call.id,
                    "call_id": call.call_id,
                    "name": call.name,
                    "arguments": call.arguments,
                })
            input_messages.extend(tool_results)

        yield _sse({"type": "usage.final", "usage": total_usage, "iterations": MAX_TOOL_ITERATIONS})
        yield _sse({"type": "stream.error", "message": "최대 툴 호출 횟수를 초과했습니다."})
        yield "data: [DONE]\n\n"

    except Exception as e:
        logger.error(f"generator_v1 오류: {e}")
        raise e
