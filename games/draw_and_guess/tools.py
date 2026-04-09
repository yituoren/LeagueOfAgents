"""Draw and Guess Tools - Image Generation"""

from __future__ import annotations

import logging
from typing import Any

from openai import AsyncOpenAI

from league.tools.base import Tool, ToolResult

logger = logging.getLogger(__name__)


class ImageGenerationTool(Tool):
    """Text-to-image generation tool

    Uses OpenAI-compatible image generation API.
    Default model: nano-banana.
    """

    def __init__(
        self,
        model: str = "nano-banana",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.name = "generate_image"
        self.description = (
            "Generate an image based on a text description. "
            "Use this tool to create a visual clue for guessers. "
            "Returns the URL of the generated image."
        )
        self.parameters = {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Text description of the image to generate. "
                    "Should be a carefully crafted prompt that hints at the target word "
                    "without being too obvious.",
                }
            },
            "required": ["prompt"],
        }
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        prompt = kwargs.get("prompt", "")
        logger.info(f"Generating image with prompt: {prompt[:80]}...")
        try:
            response = await self.client.images.generate(
                model=self.model,
                prompt=prompt,
                n=1,
            )
            image_url = response.data[0].url or ""
            logger.info(f"Image generated: {image_url[:80]}...")
            return ToolResult(
                content=f"Image generated successfully: {image_url}",
                metadata={"image_url": image_url, "prompt": prompt},
            )
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return ToolResult(
                content=f"Image generation failed: {e}",
                metadata={"error": str(e)},
            )
