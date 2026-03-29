"""
Utility functions for document processing.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Date extraction ──────────────────────────────────────────────────────────

DATE_PATTERNS = [
    # Japanese: 2024年3月15日, 令和6年3月15日
    r'(?:令和|平成|昭和)?\d{1,2}年\d{1,2}月\d{1,2}日',
    r'\d{4}年\d{1,2}月\d{1,2}日',
    # ISO: 2024-03-15, 2024/03/15
    r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
    # Short: 03/15/2024, 15.03.2024
    r'\d{1,2}[./]\d{1,2}[./]\d{4}',
]

def extract_dates(text: str) -> list[str]:
    dates = []
    for pat in DATE_PATTERNS:
        dates.extend(re.findall(pat, text))
    return list(dict.fromkeys(dates))  # dedupe, preserve order


# ─── Numeric value extraction ─────────────────────────────────────────────────

NUMERIC_PATTERNS = {
    "insulation_resistance_MΩ": r'[\d.]+\s*[MΩmΩ]+',
    "power_kW": r'[\d.,]+\s*[kK][wW]',
    "power_MW": r'[\d.,]+\s*[mM][wW]',
    "voltage_V": r'[\d.,]+\s*[vV](?:AC|DC|ac|dc)?',
    "current_A": r'[\d.,]+\s*[aA](?:C|D)?',
}

def extract_numeric_values(text: str) -> dict[str, list[str]]:
    results = {}
    for name, pat in NUMERIC_PATTERNS.items():
        found = re.findall(pat, text)
        if found:
            results[name] = list(dict.fromkeys(found))
    return results


# ─── Language detection (heuristic) ──────────────────────────────────────────

def detect_language(text: str) -> str:
    """Heuristic language detection. Returns single string: 'ja', 'en', 'ja+en', or 'unknown'."""
    if not text or not text.strip():
        return "unknown"
    has_ja = bool(re.search(r'[\u3040-\u30FF\u4E00-\u9FFF]', text))
    ascii_ratio = sum(1 for c in text if c.isascii() and c.isalpha()) / max(len(text), 1)
    threshold = 0.15 if has_ja else 0.3
    has_en = ascii_ratio > threshold
    if has_ja and has_en:
        return "ja+en"
    if has_ja:
        return "ja"
    if has_en:
        return "en"
    return "unknown"


# ─── File type detection ──────────────────────────────────────────────────────

IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.gif', '.webp'}

def is_image_file(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS

def is_pdf_file(path: str) -> bool:
    return Path(path).suffix.lower() == '.pdf'


# ─── Save/load ProcessedDocument ─────────────────────────────────────────────

def save_document(doc, output_path: str):
    """Save ProcessedDocument as JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(doc.model_dump_json(indent=2))

def load_document(path: str):
    """Load ProcessedDocument from JSON."""
    from .schema import ProcessedDocument
    with open(path, encoding="utf-8") as f:
        return ProcessedDocument.model_validate_json(f.read())


# ─── Text cleanup ─────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Basic text cleanup."""
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    # Remove null bytes
    text = text.replace('\x00', '')
    return text.strip()


# ─── Summary builder ──────────────────────────────────────────────────────────

def build_document_summary(doc) -> str:
    """
    Build a concise summary of a ProcessedDocument for agent consumption.
    """
    lines = []
    lines.append(f"FILE: {doc.file_path}")
    lines.append(f"TYPE: {doc.file_type.value} | pages={doc.page_count} | scanned={doc.is_scanned}")

    if doc.document_type_guess:
        lines.append(f"DOCUMENT TYPE: {doc.document_type_guess} (folder={doc.folder_candidate}, conf={doc.folder_confidence:.2f})")

    # Key entities
    ke = doc.key_entities
    if ke.dates:
        lines.append(f"DATES: {', '.join(ke.dates[:3])}")
    if ke.equipment_names:
        lines.append(f"EQUIPMENT: {', '.join(ke.equipment_names[:3])}")
    if ke.numeric_values:
        vals = [f"{k}={v}" for k, v in list(ke.numeric_values.items())[:3]]
        lines.append(f"VALUES: {', '.join(vals)}")
    if ke.project_name:
        lines.append(f"PROJECT: {ke.project_name}")

    # Text preview (first 200 chars)
    if doc.full_text:
        preview = clean_text(doc.full_text)[:200].replace('\n', ' ')
        lines.append(f"PREVIEW: {preview}...")

    return "\n".join(lines)
