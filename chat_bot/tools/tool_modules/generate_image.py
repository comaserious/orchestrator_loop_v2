from chat_bot.tools.registry import register_tool

@register_tool(
    parameters={
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": "The name of the image generation model to use.",
            },
            "prompt": {
                "type": "string",
                "description": "A text description of the image to generate.",
            },
        },
        "required": ["model_name", "prompt"],
    }
)
async def generate_image(model_name: str, prompt: str) -> str:
    """
    Use this tool when the user asks to create or visualize something as an image.
    It generates an image from a text prompt using an AI image generation model.
    """
    pass
