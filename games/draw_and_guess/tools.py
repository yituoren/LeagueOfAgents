"""Draw and Guess Tools - Image Generation"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from google import genai
from google.genai import types

from league.tools.base import Tool, ToolResult

logger = logging.getLogger(__name__)


class ImageGenerationTool(Tool):
    """Text-to-image generation tool

    Uses official Gemini image generation API.
    Default model: imagen-3.0-generate-002.
    """

    def __init__(
        self,
        model: str = "imagen-4.0-fast-generate-001",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.name = "generate_image"
        self.description = (
            "Generate an image based on a text description. "
            "Use this tool to create a visual clue for guessers. "
            "Returns the local file path of the generated image."
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

        # Initialize official Gemini client
        http_options = {"base_url": base_url} if base_url else None
        self.client = genai.Client(api_key=api_key, http_options=http_options)

    async def execute(self, **kwargs: Any) -> ToolResult:
        prompt = kwargs.get("prompt", "")
        logger.info(f"Generating image with prompt: {prompt[:80]}...")
        try:
            response = await self.client.aio.models.generate_images(
                model=self.model,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    output_mime_type="image/jpeg",
                ),
            )

            image_bytes = response.generated_images[0].image.image_bytes

            # Save the image locally to prevent context bloat with base64
            os.makedirs("outputs", exist_ok=True)
            filename = f"outputs/image_{uuid.uuid4().hex[:8]}.jpeg"
            with open(filename, "wb") as f:
                f.write(image_bytes)

            image_url = filename

            logger.info(f"Image generated and saved to: {image_url}")
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
