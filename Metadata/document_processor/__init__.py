"""
Document Processor Package
Handles PDF and Image file extraction for VPP AI Agent.
"""
from .schema import (
    ProcessedDocument, PageContent, TextElement, TableElement, ImageElement,
    TableCell, BBox, FileType, ElementType, ContentType, KeyEntities
)
from .pdf_processor import process_pdf, pdf_to_page_images
from .image_processor import process_image_file
from .utils import (
    extract_dates, extract_numeric_values,
    is_image_file, is_pdf_file, save_document, load_document,
    clean_text, build_document_summary
)

__all__ = [
    "ProcessedDocument", "PageContent", "TextElement", "TableElement",
    "ImageElement", "TableCell", "BBox", "FileType", "ElementType",
    "ContentType", "KeyEntities",
    "process_pdf", "pdf_to_page_images",
    "process_image_file",
    "extract_dates", "extract_numeric_values",
    "is_image_file", "is_pdf_file", "save_document", "load_document",
    "clean_text", "build_document_summary",
]
