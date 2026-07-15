"""OCR service using vision model for text extraction."""

from __future__ import annotations

from app.core.logging import get_logger
from app.services.ai.vision import VisionService

logger = get_logger(__name__)

# Default OCR prompt
_OCR_PROMPT = (
    "Please extract all visible text from this image. "
    "Preserve the original layout and structure as much as possible. "
    "Return only the extracted text without any additional commentary."
)


class OCRService:
    """Optical Character Recognition service using vision models.

    Leverages the vision model to extract text from images of documents,
    signs, labels, and other text-containing visuals.
    """

    def __init__(self) -> None:
        self._vision = VisionService()

    async def extract_text(self, image_path: str) -> str:
        """Extract text from an image using the vision model.

        Args:
            image_path: Path to the image file.

        Returns:
            Extracted text content.
        """
        logger.info("OCR extraction request", extra={"image": image_path})
        return await self._vision.analyze_image(image_path, _OCR_PROMPT)
