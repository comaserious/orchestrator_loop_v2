import logging
from playwright.async_api import async_playwright

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
async def browse_url(url: str) -> str:
    """
    Use this tool when the user asks about the contents of a specific URL.
    It loads the page in a real browser using Playwright, executes JavaScript, and returns the rendered page content 
    so the assistant can analyze and answer questions based on the live webpage.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",            # Docker 컨테이너 필수
                "--disable-dev-shm-usage", # Docker /dev/shm 용량 부족 방어
                "--disable-gpu",
            ],
        )
        try:
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15_000)
            content = await page.content()
            return content
        except Exception as e:
            logger.error(f"Error in browse_url: {e}")
            raise e
        finally:
            await browser.close()
