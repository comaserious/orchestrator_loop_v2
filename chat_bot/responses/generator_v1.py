import asyncio
import json
import logging

from openai import AsyncOpenAI

import chat_bot.tools.tool_modules  # noqa: F401 - 자동 등록 트리거
from chat_bot.tools.registry import TOOLS, TOOL_MAP
from chat_bot.responses.prompts import SYSTEM_PROMPT_BASE, build_web_search_system_prompt
from model import ChatRequest

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 10
MAX_TOOL_OUTPUT_CHARS = 20_000


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _execute_tool(name: str, args: dict) -> tuple[str, object]:
    """
    툴을 실행하고 (직렬화된 문자열, 원본 결과) 튜플을 반환.
    - 직렬화 문자열 → function_call_output에 사용
    - 원본 결과      → dict/list인 경우 후처리(시스템 프롬프트 갱신 등)에 사용
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

        # 여러 번의 LLM 호출 토큰 사용량을 누적
        total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        for iteration in range(MAX_TOOL_ITERATIONS):
            tool_calls_in_turn = []

            # ── 1단계: LLM 스트리밍 ───────────────────────────────────────────
            async for event in await client.responses.create(
                model="gpt-4.1",
                input=input_messages,
                tools=TOOLS,
                stream=True,
            ):
                yield f"data: {event.model_dump_json()}\n\n"

                # response.completed 이벤트에서 이번 턴의 토큰 사용량 누적
                if event.type == "response.completed":
                    usage = getattr(event.response, "usage", None)
                    if usage:
                        total_usage["input_tokens"]  += getattr(usage, "input_tokens",  0)
                        total_usage["output_tokens"] += getattr(usage, "output_tokens", 0)
                        total_usage["total_tokens"]  += getattr(usage, "total_tokens",  0)

                if event.type == "response.output_item.done":
                    item = event.item
                    if item.type == "function_call":
                        tool_calls_in_turn.append(item)

            # ── 2단계: 툴 호출 없음 → 최종 응답 ─────────────────────────────
            if not tool_calls_in_turn:
                yield _sse({"type": "usage.final", "usage": total_usage, "iterations": iteration + 1})
                yield _sse({"type": "stream.done", "iterations": iteration + 1})
                yield "data: [DONE]\n\n"
                return

            # ── 3단계: 툴 실행 ───────────────────────────────────────────────
            yield _sse({"type": "tools.start", "tools": [c.name for c in tool_calls_in_turn]})

            search_results_accumulated: list[dict] = []
            tool_results = []

            for call in tool_calls_in_turn:
                func_args = json.loads(call.arguments)
                yield _sse({"type": "tool.executing", "name": call.name, "args": func_args})

                try:
                    serialized, raw = await _execute_tool(call.name, func_args)

                    # search_web 결과(list[dict])를 별도로 수집
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

            # ── 4단계: 검색 결과가 있으면 시스템 프롬프트를 RAG 형식으로 교체 ──
            # input_messages[0]이 항상 system 메시지라는 구조를 유지
            if search_results_accumulated:
                input_messages[0] = {
                    "role": "system",
                    "content": build_web_search_system_prompt(search_results_accumulated),
                }

                # 프론트엔드가 [N] 마커를 인터랙티브하게 렌더링할 수 있도록
                # 번호와 출처 메타데이터를 구조화해서 미리 전송
                citations = [
                    {
                        "index": i,
                        "title": item.get("title", ""),
                        "url":   item.get("url", ""),
                    }
                    for i, item in enumerate(search_results_accumulated, start=1)
                ]
                yield _sse({"type": "citations.ready", "citations": citations})

            # ── 5단계: context 확장 후 다음 LLM 호출 ────────────────────────
            for call in tool_calls_in_turn:
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
