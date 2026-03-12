from chat_bot.tools.registry import register_tool
import dateparser
from datetime import datetime
import pytz
import httpx
import os

@register_tool(parameters={
    "type" : "object",
    "properties" : {
        "expression" : {
            "type" : "string",
            "description" : """
            The date/time expression extracted from the user's input, passed as-is.
            Examples: 'next Monday', 'last day of this month', '3rd Tuesday',
            '2 weeks from now Friday 10am', 'tomorrow 9am New York time'
            """
        },
        "timezone" : {
            "type" : "string",
            "description" : """
            IANA timezone string. Defaults to 'Asia/Seoul'.
            Examples: 'America/New_York', 'UTC', 'Europe/London'
            """,
            "default": "Asia/Seoul"
        },
        "locale" : {
            "type" : "string",
            "description" : """
            Language/region code. Defaults to 'ko_KR'.
            Examples: 'en_US', 'ja_JP', 'zh_CN'
            """,
            "default" : "ko_KR"
        }
    },
    "required" : ["expression"],
})
async def resolve_relative_datetime(
    expression: str,
    locale: str = "ko_KR",
    timezone: str = "Asia/Seoul",
)-> str:
    """
    Converts a date/time expression to an absolute ISO 8601 timestamp.
    Today's date is already provided in the system prompt, so handle simple cases directly
    and only call this tool for the following:

    Call this tool:
    - Calendar-based calculations: 'next Monday', 'last day of this month', '3rd Tuesday', 'first Monday of the year'
    - Simple relative + time combined: 'yesterday at 3pm', 'tomorrow at 9am', 'today at noon'
    - Complex compound: '2 weeks from now Friday 10am'
    - Explicit timezone conversions: '9am New York time'

    Do NOT call this tool (use the system prompt date directly):
    - Pure relative offsets with no time component: 'today', 'yesterday', 'tomorrow', 'N days/weeks ago/from now'
    - Already absolute dates: '2026-03-10', 'March 10 2026'
    """

    try:
        DUCKLING_URL = os.getenv("DUCKLING_URL", "http://duckling:8000")
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{DUCKLING_URL}/parse",
                data={
                    "text" : expression,
                    "locale" : locale,
                    "tz" : timezone,
                    "dims" : '["time"]'
                },
                headers={
                    "Content-Type" : "application/x-www-form-urlencoded"
                }
            )

            res.raise_for_status()

            data = res.json()

            print("-"*100)
            print(f"expression : {expression}")
            print(data[0]['value']['value'])
            print("-"*100)

            return data[0]['value']['value']
    except Exception as e:
        return str(datetime.now(pytz.timezone(timezone)).isoformat())
