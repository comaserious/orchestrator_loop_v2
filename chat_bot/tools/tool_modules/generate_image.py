from chat_bot.tools.registry import register_tool
from chat_bot.tools.hitl import HumanInputRequired

AVAILABLE_MODELS = ["dall-e-3", "gpt-image-1"]


@register_tool(
    parameters={
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": (
                    "The image generation model to use. "
                    "If the user has NOT specified a model, omit this field — "
                    "the system will pause and ask the user to choose."
                ),
            },
            "prompt": {
                "type": "string",
                "description": "A text description of the image to generate.",
            },
        },
        "required": ["prompt"],   # model_name 은 선택 — 없으면 HIL 발동
    }
)
async def generate_image(prompt: str, model_name: str | None = None) -> str:
    """
    Use this tool when the user asks to create or visualize something as an image.
    It generates an image from a text prompt using an AI image generation model.
    If the user has not specified which model to use, call this tool without model_name
    so the system can ask the user to choose.
    """
    if not model_name:
        raise HumanInputRequired(
            question="어떤 이미지 생성 모델을 사용할까요?",
            options=AVAILABLE_MODELS,
        )

    
    return f"[이미지 생성 완료] 모델: {model_name}, 프롬프트: {prompt}"

from openai import AsyncOpenAI

class ImageGenerator :
    def __init__(
        self,
        model_name: str,
        scale: float = 0.5,
        retry_count: int = 3,
    ):
        self.model_name = model_name
        self.scale = scale
        self.retry_count = retry_count

    def _client(self):
        return AsyncOpenAI()