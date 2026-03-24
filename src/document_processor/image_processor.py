"""
Image Processor
Handles standalone image files (PNG, JPG, TIFF, etc.) and
scanned PDF pages (rendered as images).

Pipeline:
  1. Load image
  2. Classify content type (photo / drawing / table / diagram)
  3. Basic OCR via PIL (simple heuristic) — placeholder for Tesseract/EasyOCR
  4. Vision LLM for caption + summary (OpenAI GPT-4o vision)
"""
from __future__ import annotations

import base64
import io
import logging
import os
import time
from pathlib import Path
from typing import Optional

from PIL import Image

from .schema import (
    ProcessedDocument, FileType, ContentType, KeyEntities
)

logger = logging.getLogger(__name__)


def _encode_image_base64(image_path: str) -> str:
    """Encode image file to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _encode_pil_base64(img: Image.Image, fmt: str = "PNG") -> str:
    """Encode PIL Image to base64."""
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _classify_content_type(img: Image.Image) -> ContentType:
    """
    Heuristic content type classification based on image properties.
    (Production: use a proper classifier or Vision LLM)
    """
    w, h = img.size
    aspect = w / h if h > 0 else 1.0

    # Convert to grayscale for analysis
    gray = img.convert("L")
    import statistics
    pixels = list(gray.getdata())
    try:
        std = statistics.stdev(pixels)
        mean = statistics.mean(pixels)
    except Exception:
        return ContentType.UNKNOWN

    # Heuristics:
    # - Low std + high mean → likely a document/scan (white background)
    # - Very dark with lines → likely technical drawing
    # - High color variance → likely photo
    if std < 40 and mean > 200:
        return ContentType.TABLE_SCAN  # Mostly white, likely document
    if std < 60:
        return ContentType.TECHNICAL_DRAWING
    if img.mode == "RGB":
        # Check color variance
        r, g, b = img.split()
        r_std = statistics.stdev(list(r.getdata())[:1000])
        g_std = statistics.stdev(list(g.getdata())[:1000])
        b_std = statistics.stdev(list(b.getdata())[:1000])
        avg_color_std = (r_std + g_std + b_std) / 3
        if avg_color_std > 60:
            return ContentType.PHOTO
    return ContentType.MIXED


def _load_api_key() -> Optional[str]:
    """Load OpenAI API key from .env or environment."""
    # Try environment variable first
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
    if key:
        return key
    # Try .env file (walk up from this file)
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().strip().splitlines():
            if line.startswith("OPENAI_KEY=") or line.startswith("OPENAI_API_KEY="):
                return line.split("=", 1)[1].strip()
    return None


def _call_vision_llm(
    image_b64: str,
    prompt: str,
    api_key: Optional[str] = None,
    model: str = "gpt-4o",
) -> Optional[str]:
    """Call OpenAI Vision API with an image."""
    if not api_key:
        api_key = _load_api_key()
    if not api_key:
        logger.warning("No OPENAI_API_KEY — skipping Vision LLM")
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_b64}",
                                "detail": "high",
                            },
                        },
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            max_tokens=800,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Vision LLM error: {e}")
        return None


CAPTION_PROMPT = """You are analyzing a document image from a solar power plant (VPP) construction project.
The document may be in Japanese, English, or mixed.

Provide:
1. CAPTION: A single sentence describing what this image shows.
2. DOCUMENT_TYPE: The type of document (e.g., "Test Report", "Construction Drawing", "Photo", "Equipment Spec", "Warranty Certificate", "Table of Contents", etc.)
3. KEY_INFO: Extract up to 5 key pieces of information (dates, equipment names, values, project names).
4. FOLDER_NUMBER: Which folder number (1-22) best matches this document based on the sort rules?

Respond in this exact JSON format:
{
  "caption": "...",
  "document_type": "...",
  "key_info": ["item1", "item2"],
  "folder_number": 7,
  "folder_confidence": 0.85,
  "language": "ja"
}"""


def process_image_file(
    file_path: str,
    task_id: Optional[str] = None,
    use_vision_llm: bool = False,
    openai_api_key: Optional[str] = None,
    max_size: tuple[int, int] = (2048, 2048),
) -> ProcessedDocument:
    """
    Process a standalone image file.
    Returns ProcessedDocument.
    """
    start = time.time()
    doc = ProcessedDocument(
        file_path=file_path,
        file_type=FileType.IMAGE,
        task_id=task_id,
        processing_method="pil" + ("+vision_llm" if use_vision_llm else ""),
    )

    try:
        img = Image.open(file_path)
        doc.content_type = _classify_content_type(img)

        # Resize if too large for API
        img_copy = img.copy()
        img_copy.thumbnail(max_size, Image.LANCZOS)

        if use_vision_llm:
            img_b64 = _encode_pil_base64(img_copy)
            raw_response = _call_vision_llm(img_b64, CAPTION_PROMPT, openai_api_key)
            if raw_response:
                import json, re
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
                if json_match:
                    try:
                        parsed = json.loads(json_match.group())
                        doc.image_caption = parsed.get("caption")
                        doc.image_summary = parsed.get("document_type")
                        doc.document_type_guess = parsed.get("document_type")
                        doc.folder_candidate = parsed.get("folder_number")
                        doc.folder_confidence = parsed.get("folder_confidence", 0.0)
                        key_info = parsed.get("key_info", [])
                        doc.full_text = doc.image_caption or ""
                        if key_info:
                            doc.full_text += "\n" + "\n".join(str(k) for k in key_info)
                    except json.JSONDecodeError:
                        doc.image_caption = raw_response[:200]
                        doc.full_text = raw_response
                else:
                    doc.image_caption = raw_response[:200]
                    doc.full_text = raw_response

    except Exception as e:
        doc.error = str(e)
        logger.error(f"Image processing failed for {file_path}: {e}")

    doc.processing_time_sec = round(time.time() - start, 3)
    return doc


def process_scanned_pdf_page(
    image_path: str,
    page_index: int,
    use_vision_llm: bool = False,
    openai_api_key: Optional[str] = None,
) -> dict:
    """
    Process a single rendered page from a scanned PDF.
    Returns dict with caption, summary, ocr_text.
    """
    result = {
        "page_index": page_index,
        "image_path": image_path,
        "caption": None,
        "summary": None,
        "ocr_text": None,
    }

    try:
        if use_vision_llm:
            img_b64 = _encode_image_base64(image_path)
            raw = _call_vision_llm(img_b64, CAPTION_PROMPT, openai_api_key)
            if raw:
                result["caption"] = raw[:200]
                result["summary"] = raw
    except Exception as e:
        logger.error(f"Scanned page processing error: {e}")

    return result
