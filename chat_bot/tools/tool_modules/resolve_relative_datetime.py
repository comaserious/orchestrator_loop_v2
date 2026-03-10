from chat_bot.tools.registry import register_tool
import dateparser
from datetime import datetime
import pytz

@register_tool(parameters={
    "type" : "object",
    "properties" : {
        "expression" : {
            "type" : "string",
            "description" : """
            사용자가 언급한 날짜/시간 표현을 그대로 추출하여 전달합니다.
            예: '오늘', '내일', '어제', '3일 후', '다음 주 월요일', 
            '지난달 말', '이번 주 금요일', '2시간 전', 'now'
            """
        },
        "timezone" : {
            "type" : "string",
            "description" : """
            IANA 타임존 문자열. 생략 시 기본값은 'Asia/Seoul'. 
            예: 'America/New_York', 'UTC', 'Europe/London'
            """,
            "default": "Asia/Seoul"
        }
    },
    "required" : ["expression"],
}) 
def resolve_relative_datetime(
    expression: str,
    timezone: str = "Asia/Seoul",
):
    """
    사용자가 말한 날짜/시간 표현(상대적 표현 포함)을 절대 시간으로 변환합니다. 
    '오늘', '내일', '어제', '3일 후', '다음 주 월요일', '지난달' 같은 상대적 표현이나 
    '2024년 3월 5일' 같은 절대 표현 모두 처리할 수 있습니다. 
    날짜/시간과 관련된 모든 질문에서 LLM이 직접 날짜를 추론하거나 계산하지 말고 
    반드시 이 툴을 호출하여 정확한 절대 시간을 얻은 후 답변하세요. 
    기본 타임존은 Asia/Seoul(KST, UTC+9)입니다.
    """
    
    anchor = datetime.now(pytz.timezone(timezone))
    settings = {
        "TIMEZONE": timezone,
        "RETURN_AS_TIMEZONE_AWARE": True,
        "RELATIVE_BASE": anchor,
        "PREFER_DAY_OF_MONTH": "first",
        "PREFER_DATES_FROM": "future"  # '다음 주' 등 미래 표현 우선
    }

    dt = dateparser.parse(
        expression,
        languages=["ko"],
        settings=settings
    )

    print("-"*100)
    print(dt)
    print("-"*100)

    if dt is None:
        raise ValueError(f"Cannot parse datetime expression: {expression}")

    return dt.isoformat()