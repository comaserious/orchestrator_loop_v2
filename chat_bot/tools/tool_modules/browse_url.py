import logging
from playwright.sync_api import sync_playwright

from chat_bot.tools.registry import register_tool

logger = logging.getLogger(__name__)

@register_tool(
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL of the page to browse.",
            }
        },
        "required": ["url"],
    }
)
def browse_url(url: str) -> str:
    """
    Use this tool when the user asks about the contents of a specific URL.
    It loads the page in a real browser using Playwright, executes JavaScript, and returns the rendered page content 
    so the assistant can analyze and answer questions based on the live webpage.
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",           # Docker 컨테이너 필수
                    "--disable-dev-shm-usage", # Docker /dev/shm 용량 부족 방어
                    "--disable-gpu",
                ],
            )
            page = browser.new_page()
            # "networkidle"은 analytics·polling 등으로 타임아웃 빈발
            # "domcontentloaded" : DOM 파싱 완료 시점 → 대부분의 텍스트 콘텐츠 확보 가능
            page.goto(url, wait_until="domcontentloaded", timeout=15_000)
            content = page.content()
            browser.close()
            return content
    except Exception as e:
        logger.error(f"Error in browse_url: {e}")
        raise e

    finally:
        browser.close()
        page.close()