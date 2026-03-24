"""
PDF Processor
Extracts text, tables, and images from PDF files.
Strategy:
  1. Try PyMuPDF for fast text + image extraction
  2. Use pdfplumber for improved table extraction
  3. Detect if PDF is scanned (no text layer)
"""
from __future__ import annotations

import io
import os
import time
import logging
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pdfplumber
from PIL import Image

from .schema import (
    ProcessedDocument, PageContent, TextElement, TableElement, ImageElement,
    TableCell, BBox, FileType, ElementType, KeyEntities
)

logger = logging.getLogger(__name__)

# Threshold: if text chars per page < this, consider scanned
SCANNED_THRESHOLD = 30


def _bbox_from_fitz(rect) -> BBox:
    return BBox(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1)


def _detect_text_layer(fitz_doc: fitz.Document) -> tuple[bool, bool]:
    """
    Returns (has_text_layer, is_scanned).
    Samples first 3 pages.
    """
    sample_pages = min(3, fitz_doc.page_count)
    total_chars = 0
    for i in range(sample_pages):
        page = fitz_doc[i]
        total_chars += len(page.get_text("text").strip())
    avg_chars = total_chars / max(sample_pages, 1)
    has_text = avg_chars > SCANNED_THRESHOLD
    return has_text, not has_text


def _extract_text_pymupdf(page: fitz.Page) -> list[TextElement]:
    """Extract text blocks with bbox."""
    elements = []
    blocks = page.get_text("dict")["blocks"]
    for block in blocks:
        if block["type"] != 0:  # 0 = text
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                bbox_raw = span.get("bbox", (0, 0, 0, 0))
                elements.append(TextElement(
                    content=text,
                    bbox=BBox(x0=bbox_raw[0], y0=bbox_raw[1], x1=bbox_raw[2], y1=bbox_raw[3]),
                    font_size=span.get("size"),
                    is_bold="Bold" in span.get("font", ""),
                ))
    return elements


def _extract_tables_pdfplumber(plumber_page) -> list[TableElement]:
    """Extract tables using pdfplumber (better table detection)."""
    elements = []
    try:
        tables = plumber_page.extract_tables()
        table_bboxes = plumber_page.find_tables()
        for i, (table_data, table_obj) in enumerate(zip(tables, table_bboxes)):
            if not table_data:
                continue
            cells = []
            raw_text_rows = []
            for row_idx, row in enumerate(table_data):
                row_texts = []
                for col_idx, cell in enumerate(row):
                    cell_val = str(cell or "").strip()
                    row_texts.append(cell_val)
                    cells.append(TableCell(
                        row=row_idx,
                        col=col_idx,
                        value=cell_val,
                        is_header=(row_idx == 0),
                    ))
                raw_text_rows.append(" | ".join(row_texts))

            bbox_raw = table_obj.bbox  # (x0, top, x1, bottom)
            elements.append(TableElement(
                content="\n".join(raw_text_rows),
                bbox=BBox(x0=bbox_raw[0], y0=bbox_raw[1], x1=bbox_raw[2], y1=bbox_raw[3]),
                cells=cells,
                num_rows=len(table_data),
                num_cols=max(len(r) for r in table_data) if table_data else 0,
            ))
    except Exception as e:
        logger.debug(f"pdfplumber table extraction error: {e}")
    return elements


def _extract_images_pymupdf(
    fitz_page: fitz.Page,
    fitz_doc: fitz.Document,
    output_dir: Optional[str] = None,
    page_index: int = 0,
) -> list[ImageElement]:
    """Extract embedded images from a PDF page."""
    elements = []
    image_list = fitz_page.get_images(full=True)
    for img_idx, img_info in enumerate(image_list):
        xref = img_info[0]
        try:
            base_image = fitz_doc.extract_image(xref)
            image_bytes = base_image["image"]
            ext = base_image["ext"]
            width = base_image["width"]
            height = base_image["height"]

            # Save image if output dir provided
            img_path = None
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
                img_path = os.path.join(output_dir, f"p{page_index}_img{img_idx}.{ext}")
                with open(img_path, "wb") as f:
                    f.write(image_bytes)

            # Get bbox from page (approximate)
            img_rects = fitz_page.get_image_rects(xref)
            bbox = _bbox_from_fitz(img_rects[0]) if img_rects else None

            elements.append(ImageElement(
                bbox=bbox,
                image_index=img_idx,
                image_path=img_path,
                width=width,
                height=height,
            ))
        except Exception as e:
            logger.debug(f"Image extraction error (xref={xref}): {e}")
    return elements


def process_pdf(
    file_path: str,
    task_id: Optional[str] = None,
    extract_images: bool = True,
    image_output_dir: Optional[str] = None,
    use_pdfplumber_tables: bool = True,
) -> ProcessedDocument:
    """
    Main PDF processing function.
    Returns a ProcessedDocument with all extracted content.
    """
    start = time.time()
    doc = ProcessedDocument(
        file_path=file_path,
        file_type=FileType.PDF,
        task_id=task_id,
    )

    try:
        fitz_doc = fitz.open(file_path)
        doc.page_count = fitz_doc.page_count

        # Detect text layer
        has_text, is_scanned = _detect_text_layer(fitz_doc)
        doc.has_text_layer = has_text
        doc.is_scanned = is_scanned
        doc.processing_method = "pymupdf" + ("+pdfplumber" if use_pdfplumber_tables else "")

        if is_scanned:
            logger.info(f"  [SCANNED] {Path(file_path).name} — no text layer detected")
            # For scanned PDFs, we still extract any images
            # (Vision LLM would be called separately)
            for page_idx in range(fitz_doc.page_count):
                fitz_page = fitz_doc[page_idx]
                page = PageContent(
                    page_index=page_idx,
                    width=fitz_page.rect.width,
                    height=fitz_page.rect.height,
                )
                if extract_images and image_output_dir:
                    page_img_dir = os.path.join(image_output_dir, f"page_{page_idx}")
                    img_elements = _extract_images_pymupdf(fitz_page, fitz_doc, page_img_dir, page_idx)
                    page.elements.extend(img_elements)
                doc.pages.append(page)
        else:
            # Has text layer: use pdfplumber for tables, PyMuPDF for text+images
            plumber_doc = pdfplumber.open(file_path) if use_pdfplumber_tables else None

            for page_idx in range(fitz_doc.page_count):
                fitz_page = fitz_doc[page_idx]
                page = PageContent(
                    page_index=page_idx,
                    width=fitz_page.rect.width,
                    height=fitz_page.rect.height,
                )

                # 1. Text elements via PyMuPDF
                text_elements = _extract_text_pymupdf(fitz_page)
                page.elements.extend(text_elements)

                # 2. Table elements via pdfplumber (replaces table text from above)
                if plumber_doc and page_idx < len(plumber_doc.pages):
                    table_elements = _extract_tables_pdfplumber(plumber_doc.pages[page_idx])
                    page.elements.extend(table_elements)

                # 3. Image elements
                if extract_images:
                    img_out = os.path.join(image_output_dir, f"page_{page_idx}") if image_output_dir else None
                    img_elements = _extract_images_pymupdf(fitz_page, fitz_doc, img_out, page_idx)
                    page.elements.extend(img_elements)

                doc.pages.append(page)

            if plumber_doc:
                plumber_doc.close()
        fitz_doc.close()

        # Build full_text from all pages
        all_texts = []
        for page in doc.pages:
            all_texts.append(page.full_text)
        doc.full_text = "\n\n".join(t for t in all_texts if t.strip())

    except Exception as e:
        doc.error = str(e)
        logger.error(f"PDF processing failed for {file_path}: {e}")

    doc.processing_time_sec = round(time.time() - start, 3)
    return doc


def pdf_to_page_images(
    file_path: str,
    output_dir: str,
    dpi: int = 150,
) -> list[str]:
    """
    Render each PDF page as a PNG image.
    Used for scanned PDFs before Vision LLM processing.
    Returns list of saved image paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    try:
        fitz_doc = fitz.open(file_path)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        for page_idx in range(fitz_doc.page_count):
            page = fitz_doc[page_idx]
            pix = page.get_pixmap(matrix=mat)
            out_path = os.path.join(output_dir, f"page_{page_idx:03d}.png")
            pix.save(out_path)
            paths.append(out_path)
        fitz_doc.close()
    except Exception as e:
        logger.error(f"PDF render error: {e}")
    return paths
