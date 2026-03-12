import asyncio
import json
import logging
from uuid import uuid4

from openai import AsyncOpenAI

import chat_bot.tools.tool_modules  # noqa: F401 — auto-register function tools
import chat_bot.tools.mcp_modules   # noqa: F401 — auto-register MCP tools
from chat_bot.tools.registry import TOOLS, MCP_TOOLS, TOOL_MAP
from chat_bot.tools.hitl import HumanInputRequired
from chat_bot.responses.prompts import build_web_search_system_prompt, get_system_prompt_base
from model import ChatRequest

logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS   = 10
MAX_TOOL_OUTPUT_CHARS = 20_000
OLD_OUTPUT_MAX_CHARS  = 300   # Tier 2: max chars retained for old tool outputs

# In-memory store for pending HIL sessions
SESSION_STORE: dict[str, dict] = {}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _compress_old_outputs(messages: list) -> None:
    """Tier 2: truncate all but the last function_call_output to OLD_OUTPUT_MAX_CHARS."""
    indices = [
        i for i, m in enumerate(messages)
        if isinstance(m, dict) and m.get("type") == "function_call_output"
    ]
    for i in indices[:-1]:  # 마지막(Tier 3)은 건드리지 않음
        out = messages[i].get("output", "")
        if len(out) > OLD_OUTPUT_MAX_CHARS:
            messages[i] = {**messages[i], "output": out[:OLD_OUTPUT_MAX_CHARS] + " ... [truncated]"}


async def _execute_tool(name: str, args: dict) -> tuple[str, object]:
    """
    function 툴을 실행. MCP 툴은 OpenAI 서버 측에서 처리되므로 여기서 실행하지 않음.
    HumanInputRequired 예외는 호출부에서 직접 처리.
    """
    fn = TOOL_MAP.get(name)
    if fn is None:
        raise ValueError(f"Unregistered tool: '{name}'")

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
    model_name: str = "gpt-4.1",
    start_iteration: int = 0,
    search_results_accumulated: list | None = None,
):
    """Core orchestrator loop — shared by generator_v1 and resume_generator."""
    if search_results_accumulated is None:
        search_results_accumulated = []

    for iteration in range(start_iteration, MAX_TOOL_ITERATIONS):
        function_calls_in_turn = []
        tools_panel_opened = False

        # ── Step 1: LLM streaming ───────────────────────────────────────
        async for event in await client.responses.create(
            model=model_name,
            input=input_messages,
            tools=TOOLS + MCP_TOOLS + [{"type" : "image_generation"}],
            stream=True,
        ):
            yield f"data: {event.model_dump_json()}\n\n"

            if event.type == "response.completed":
                # accumulate token usage
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


        # ── Step 2: no function calls → final response ──────────────────
        if not function_calls_in_turn:
            yield _sse({"type": "usage.final", "usage": total_usage, "iterations": iteration + 1})
            yield _sse({"type": "stream.done", "iterations": iteration + 1})
            yield "data: [DONE]\n\n"
            return

        # ── Step 3: execute function calls ──────────────────────────────
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
                    # results injected into system prompt — replace output with placeholder
                    serialized = "[Search results injected into system prompt]"

                yield _sse({"type": "tool.done", "name": call.name})
                tool_results.append({
                    "type":    "function_call_output",
                    "call_id": call.call_id,
                    "output":  serialized,
                })

            except HumanInputRequired as hitl:
                # ── HIL: save session → send SSE → suspend stream ───────
                session_id = str(uuid4())
                SESSION_STORE[session_id] = {
                    "messages":       list(input_messages),
                    "call": {
                        "id":        call.id,
                        "call_id":   call.call_id,
                        "name":      call.name,
                        "arguments": call.arguments,
                    },
                    "model_name":     model_name,
                    "func_args":      func_args,
                    "search_results": list(search_results_accumulated),
                    "total_usage":    dict(total_usage),
                    "iteration":      iteration,
                }
                yield _sse({
                    "type":       "human_input.required",
                    "session_id": session_id,
                    "question":   hitl.question,
                    "model_name": model_name,
                    "options":    hitl.options,
                })
                yield "data: [DONE]\n\n"
                return

            except Exception as e:
                serialized = f"[Error] Tool '{call.name}' failed: {e}"
                logger.error(serialized)
                yield _sse({"type": "tool.error", "name": call.name, "error": str(e)})
                tool_results.append({
                    "type":    "function_call_output",
                    "call_id": call.call_id,
                    "output":  serialized,
                })

        # ── Step 4: inject search results into system prompt ────────────
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

        # ── Step 5: compress old outputs, extend context, next LLM call ─
        _compress_old_outputs(input_messages)
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
    yield _sse({"type": "stream.error", "message": "Maximum tool iterations exceeded."})
    yield "data: [DONE]\n\n"


async def generator_v1(request: ChatRequest):
    try:
        client = AsyncOpenAI()
        input_messages = [
            {"role": "system", "content": get_system_prompt_base()},
            {"role": "user",   "content": request.message},
        ]
        total_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}

        async for chunk in _orchestrator_loop(client, input_messages, total_usage, request.model_name):
            yield chunk

    except Exception as e:
        logger.error(f"generator_v1 error: {e}")
        raise e


async def resume_generator(session_id: str, choice: str):
    """Resume the orchestrator after a HIL user selection."""
    session = SESSION_STORE.pop(session_id, None)
    if not session:
        yield _sse({"type": "stream.error", "message": "Session not found (expired or invalid ID)."})
        yield "data: [DONE]\n\n"
        return

    messages       = session["messages"]
    call_data      = session["call"]
    model_name     = session["model_name"]
    func_args      = session["func_args"]
    search_results = session["search_results"]
    total_usage    = session["total_usage"]
    next_iteration = session["iteration"] + 1

    # apply user selection to args and execute tool
    func_args["model_name"] = choice
    try:
        serialized, _ = await _execute_tool(call_data["name"], func_args)
    except Exception as e:
        yield _sse({"type": "stream.error", "message": f"Image generation failed: {e}"})
        yield "data: [DONE]\n\n"
        return

    # extend context (equivalent to Step 5)
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
            model_name=model_name,
            start_iteration=next_iteration,
            search_results_accumulated=search_results,
        ):
            yield chunk

    except Exception as e:
        logger.error(f"resume_generator error: {e}")
        raise e
