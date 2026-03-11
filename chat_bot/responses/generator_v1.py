import asyncio
import json
import logging
from uuid import uuid4

from openai import AsyncOpenAI

import chat_bot.tools.tool_modules  # noqa: F401 - function 툴 자동 등록
import chat_bot.tools.mcp_modules   # noqa: F401 - MCP 툴 자동 등록
from chat_bot.tools.registry import TOOLS, MCP_TOOLS, TOOL_MAP
from chat_bot.tools.hitl import HumanInputRequired
from chat_bot.responses.prompts import build_web_search_system_prompt, get_system_prompt_base
from model import ChatRequest

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS  = 10
MAX_TOOL_OUTPUT_CHARS = 20_000

# HIL 대기 세션 저장소 (메모리)
SESSION_STORE: dict[str, dict] = {}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _execute_tool(name: str, args: dict) -> tuple[str, object]:
    """
    function 툴을 실행. MCP 툴은 OpenAI 서버 측에서 처리되므로 여기서 실행하지 않음.
    HumanInputRequired 예외는 호출부에서 직접 처리.
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


async def _orchestrator_loop(
    client: AsyncOpenAI,
    input_messages: list,
    total_usage: dict,
    start_iteration: int = 0,
    search_results_accumulated: list | None = None,
):
    """핵심 오케스트레이터 루프 — generator_v1 과 resume_generator 가 공유."""
    if search_results_accumulated is None:
        search_results_accumulated = []

    for iteration in range(start_iteration, MAX_TOOL_ITERATIONS):
        function_calls_in_turn = []
        tools_panel_opened = False

        # ── 1단계: LLM 스트리밍 ─────────────────────────────────────────
        async for event in await client.responses.create(
            model="gpt-4.1",
            input=input_messages,
            tools=TOOLS + MCP_TOOLS + [{"type" : "image_generation"}],
            stream=True,
        ):
            yield f"data: {event.model_dump_json()}\n\n"

            if event.type == "response.completed":
                usage = getattr(event.response, "usage", None)
                if usage:
                    total_usage["input_tokens"]  += getattr(usage, "input_tokens",  0)
                    total_usage["output_tokens"] += getattr(usage, "output_tokens", 0)
                    total_usage["total_tokens"]  += getattr(usage, "total_tokens",  0)

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

                if getattr(item, "type", None) == "image_generation_call":
                    if not tools_panel_opened:
                        yield _sse({"type" : "tools.start", "tools" : ["generate_image"]})

            elif event.type == "response.output_item.done":
                item = event.item
                if getattr(item, "type", None) == "mcp_call":
                    if item.error:
                        yield _sse({"type": "tool.error", "name": item.name, "error": item.error})
                    else:
                        yield _sse({"type": "tool.done", "name": item.name})
                elif getattr(item, "type", None) == "function_call":
                    function_calls_in_turn.append(item)

                elif item.type == "image_generation_call" and getattr(item, "result", None):
                    b64 = item.result
                    yield _sse({
                        "type": "image_final",
                        "b64": b64
                    })

            elif event.type == "response.image_generation_call.partial_image":
                b64 = event.partial_image_b64
                yield _sse({"type" : "image_preview", "b64": b64})

            
            


        # ── 2단계: function_call 없으면 최종 응답 ────────────────────────
        if not function_calls_in_turn:
            yield _sse({"type": "usage.final", "usage": total_usage, "iterations": iteration + 1})
            yield _sse({"type": "stream.done", "iterations": iteration + 1})
            yield "data: [DONE]\n\n"
            return

        # ── 3단계: function_call 실행 ─────────────────────────────────────
        if not tools_panel_opened:
            yield _sse({"type": "tools.start", "tools": [c.name for c in function_calls_in_turn]})
            tools_panel_opened = True

        tool_results: list[dict] = []

        for call in function_calls_in_turn:
            func_args = json.loads(call.arguments)
            yield _sse({"type": "tool.executing", "name": call.name, "args": func_args})

            try:
                serialized, raw = await _execute_tool(call.name, func_args)

                if call.name == "search_web" and isinstance(raw, list):
                    search_results_accumulated.extend(raw)

                yield _sse({"type": "tool.done", "name": call.name})
                tool_results.append({
                    "type":    "function_call_output",
                    "call_id": call.call_id,
                    "output":  serialized,
                })

            except HumanInputRequired as hitl:
                # ── HIL: 세션 저장 → SSE 전송 → 스트림 일시 중단 ──────────
                session_id = str(uuid4())
                SESSION_STORE[session_id] = {
                    "messages":       list(input_messages),
                    "call": {
                        "id":        call.id,
                        "call_id":   call.call_id,
                        "name":      call.name,
                        "arguments": call.arguments,
                    },
                    "func_args":      func_args,
                    "search_results": list(search_results_accumulated),
                    "total_usage":    dict(total_usage),
                    "iteration":      iteration,
                }
                yield _sse({
                    "type":       "human_input.required",
                    "session_id": session_id,
                    "question":   hitl.question,
                    "options":    hitl.options,
                })
                yield "data: [DONE]\n\n"
                return

            except Exception as e:
                serialized = f"[오류] {call.name} 실행 실패: {e}"
                logger.error(serialized)
                yield _sse({"type": "tool.error", "name": call.name, "error": str(e)})
                tool_results.append({
                    "type":    "function_call_output",
                    "call_id": call.call_id,
                    "output":  serialized,
                })

        # ── 4단계: 검색 결과가 있으면 RAG 프롬프트 교체 ─────────────────
        if search_results_accumulated:
            input_messages[0] = {
                "role":    "system",
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
                "type":      "function_call",
                "id":        call.id,
                "call_id":   call.call_id,
                "name":      call.name,
                "arguments": call.arguments,
            })
        input_messages.extend(tool_results)

    yield _sse({"type": "usage.final", "usage": total_usage, "iterations": MAX_TOOL_ITERATIONS})
    yield _sse({"type": "stream.error", "message": "최대 툴 호출 횟수를 초과했습니다."})
    yield "data: [DONE]\n\n"


async def generator_v1(request: ChatRequest):
    try:
        client = AsyncOpenAI()
        input_messages = [
            {"role": "system", "content": get_system_prompt_base()},
            {"role": "user",   "content": request.message},
        ]
        total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        async for chunk in _orchestrator_loop(client, input_messages, total_usage):
            yield chunk

    except Exception as e:
        logger.error(f"generator_v1 오류: {e}")
        raise e


async def resume_generator(session_id: str, choice: str):
    """HIL 사용자 선택 후 오케스트레이터를 재개."""
    session = SESSION_STORE.pop(session_id, None)
    if not session:
        yield _sse({"type": "stream.error", "message": "세션을 찾을 수 없습니다 (만료 또는 잘못된 ID)."})
        yield "data: [DONE]\n\n"
        return

    messages       = session["messages"]
    call_data      = session["call"]
    func_args      = session["func_args"]
    search_results = session["search_results"]
    total_usage    = session["total_usage"]
    next_iteration = session["iteration"] + 1

    # 사용자 선택을 args 에 반영 후 실제 툴 실행
    func_args["model_name"] = choice
    try:
        serialized, _ = await _execute_tool(call_data["name"], func_args)
    except Exception as e:
        yield _sse({"type": "stream.error", "message": f"이미지 생성 실패: {e}"})
        yield "data: [DONE]\n\n"
        return

    # context 확장 (step 5 에 해당)
    messages.append({
        "type":      "function_call",
        "id":        call_data["id"],
        "call_id":   call_data["call_id"],
        "name":      call_data["name"],
        "arguments": call_data["arguments"],
    })
    messages.append({
        "type":    "function_call_output",
        "call_id": call_data["call_id"],
        "output":  serialized,
    })

    try:
        client = AsyncOpenAI()
        async for chunk in _orchestrator_loop(
            client,
            messages,
            total_usage,
            start_iteration=next_iteration,
            search_results_accumulated=search_results,
        ):
            yield chunk

    except Exception as e:
        logger.error(f"resume_generator 오류: {e}")
        raise e
