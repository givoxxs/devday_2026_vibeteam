"""
Document Processing Schema
Defines all data structures for extracted document content.
"""
from __future__ import annotations
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field


# ─── Enums ────────────────────────────────────────────────────────────────────

class ElementType(str, Enum):
    TEXT = "text"
    TABLE = "table"
    IMAGE = "image"
    HEADER = "header"
    FOOTER = "footer"

class FileType(str, Enum):
    PDF = "pdf"
    IMAGE = "image"
    XLSX = "xlsx"
    DOCX = "docx"
    DOC = "doc"

class ContentType(str, Enum):
    """For standalone image files"""
    PHOTO = "photo"
    TECHNICAL_DRAWING = "technical_drawing"
    TABLE_SCAN = "table_scan"
    DIAGRAM = "diagram"
    HANDWRITTEN = "handwritten"
    MIXED = "mixed"
    UNKNOWN = "unknown"


# ─── BBox ─────────────────────────────────────────────────────────────────────

class BBox(BaseModel):
    """Bounding box on a page (in points for PDF, pixels for image)."""
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0


# ─── Table Cell ───────────────────────────────────────────────────────────────

class TableCell(BaseModel):
    row: int
    col: int
    value: str
    is_header: bool = False
    row_span: int = 1
    col_span: int = 1


# ─── Page Elements ────────────────────────────────────────────────────────────

class TextElement(BaseModel):
    element_type: ElementType = ElementType.TEXT
    content: str
    bbox: Optional[BBox] = None
    font_size: Optional[float] = None
    is_bold: bool = False

class TableElement(BaseModel):
    element_type: ElementType = ElementType.TABLE
    content: str                    # raw text fallback
    bbox: Optional[BBox] = None
    cells: list[TableCell] = Field(default_factory=list)
    num_rows: int = 0
    num_cols: int = 0

    def to_markdown(self) -> str:
        """Convert table to markdown string."""
        if not self.cells:
            return self.content
        rows: dict[int, dict[int, str]] = {}
        for c in self.cells:
            rows.setdefault(c.row, {})[c.col] = c.value
        lines = []
        for row_idx in sorted(rows.keys()):
            row = rows[row_idx]
            line = "| " + " | ".join(row.get(ci, "") for ci in range(max(row.keys()) + 1)) + " |"
            lines.append(line)
            if row_idx == 0:
                lines.append("|" + "|".join(["---"] * (max(row.keys()) + 1)) + "|")
        return "\n".join(lines)

class ImageElement(BaseModel):
    element_type: ElementType = ElementType.IMAGE
    bbox: Optional[BBox] = None
    image_index: int = 0            # index of image within page
    image_path: Optional[str] = None  # saved path if extracted
    width: Optional[int] = None
    height: Optional[int] = None
    caption: Optional[str] = None   # from Vision LLM
    summary: Optional[str] = None   # from Vision LLM
    ocr_text: Optional[str] = None  # from OCR


# ─── Page ─────────────────────────────────────────────────────────────────────

class PageContent(BaseModel):
    page_index: int
    width: float = 0
    height: float = 0
    elements: list[TextElement | TableElement | ImageElement] = Field(default_factory=list)
    ocr_text: Optional[str] = None  # Vision LLM output for scanned pages

    @property
    def full_text(self) -> str:
        if self.ocr_text:
            return self.ocr_text
        parts = []
        for e in self.elements:
            if isinstance(e, TextElement):
                parts.append(e.content)
            elif isinstance(e, TableElement):
                parts.append(e.to_markdown())
        return "\n".join(parts)


# ─── File-level Key Entities ──────────────────────────────────────────────────

class KeyEntities(BaseModel):
    dates: list[str] = Field(default_factory=list)
    equipment_names: list[str] = Field(default_factory=list)
    numeric_values: dict[str, str] = Field(default_factory=dict)  # {"điện trở cách điện": "≥1MΩ"}
    project_name: Optional[str] = None
    site_id: Optional[str] = None
    company_names: list[str] = Field(default_factory=list)


# ─── Document (top-level) ─────────────────────────────────────────────────────

class ProcessedDocument(BaseModel):
    """Complete processed representation of a single file."""

    # Source info
    file_path: str
    file_type: FileType
    task_id: Optional[str] = None

    # PDF-specific
    page_count: int = 0
    pages: list[PageContent] = Field(default_factory=list)

    # Image-specific (when file itself is an image)
    content_type: Optional[ContentType] = None
    image_path: Optional[str] = None
    image_caption: Optional[str] = None
    image_summary: Optional[str] = None
    image_ocr_text: Optional[str] = None

    # Derived fields (populated after processing)
    full_text: str = ""             # concatenated text from all pages
    document_type_guess: Optional[str] = None   # e.g. "Test Report"
    folder_candidate: Optional[int] = None      # e.g. 7
    folder_confidence: float = 0.0
    key_entities: KeyEntities = Field(default_factory=KeyEntities)

    # Processing metadata
    processing_method: str = ""     # "pymupdf", "pdfplumber", "vision_llm", etc.
    processing_time_sec: float = 0.0
    has_text_layer: bool = True
    is_scanned: bool = False
    error: Optional[str] = None

    @property
    def summary_for_agent(self) -> str:
        """Short summary to feed into agent context."""
        parts = [f"[{self.file_type.value.upper()}] {self.file_path}"]
        if self.document_type_guess:
            parts.append(f"Type: {self.document_type_guess}")
        if self.folder_candidate:
            parts.append(f"Folder: {self.folder_candidate} (conf={self.folder_confidence:.2f})")
        if self.full_text:
            parts.append(f"Text preview: {self.full_text[:300]}...")
        return "\n".join(parts)
