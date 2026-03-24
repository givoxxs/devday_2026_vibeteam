"""
Experiment 01: PDF Processing Benchmark
Benchmarks PyMuPDF vs pdfplumber on actual task data.
Analyzes: text quality, table detection, images, scanned detection, speed.

Run: conda run -n devday python experiments/toan/01_pdf_benchmark.py
"""
import json
import os
import sys
import time
import statistics
from pathlib import Path
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import fitz
import pdfplumber
from tqdm import tqdm

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def sample_pdfs(n_per_task: int = 2) -> list[Path]:
    """Get sample PDFs from each task."""
    pdfs = []
    for task_dir in sorted(DATA_DIR.iterdir()):
        if not task_dir.is_dir():
            continue
        task_pdfs = list(task_dir.rglob("*.pdf"))
        pdfs.extend(task_pdfs[:n_per_task])
    return pdfs


def benchmark_pymupdf(pdf_path: Path) -> dict:
    """Benchmark PyMuPDF on a single PDF."""
    result = {"path": str(pdf_path), "tool": "pymupdf", "error": None}
    start = time.time()
    try:
        doc = fitz.open(str(pdf_path))
        n_pages = doc.page_count
        result["page_count"] = n_pages

        total_chars = 0
        total_text_blocks = 0
        total_images = 0
        total_tables_approx = 0
        page_stats = []

        for page_idx in range(n_pages):
            page = doc[page_idx]
            text = page.get_text("text")
            blocks = page.get_text("dict")["blocks"]
            images = page.get_images(full=True)

            chars = len(text.strip())
            txt_blocks = sum(1 for b in blocks if b["type"] == 0)
            img_count = len(images)

            total_chars += chars
            total_text_blocks += txt_blocks
            total_images += img_count

            page_stats.append({
                "page": page_idx,
                "chars": chars,
                "text_blocks": txt_blocks,
                "images": img_count,
            })

        doc.close()

        result.update({
            "total_chars": total_chars,
            "total_text_blocks": total_text_blocks,
            "total_images": total_images,
            "avg_chars_per_page": total_chars / max(n_pages, 1),
            "has_text": total_chars > 30 * n_pages,
            "is_scanned": total_chars < 30 * max(n_pages, 1),
            "page_stats": page_stats[:3],  # first 3 pages only for report
        })
    except Exception as e:
        result["error"] = str(e)
    result["time_sec"] = round(time.time() - start, 4)
    return result


def benchmark_pdfplumber(pdf_path: Path) -> dict:
    """Benchmark pdfplumber on a single PDF."""
    result = {"path": str(pdf_path), "tool": "pdfplumber", "error": None}
    start = time.time()
    try:
        with pdfplumber.open(str(pdf_path)) as doc:
            result["page_count"] = len(doc.pages)

            total_chars = 0
            total_tables = 0
            total_table_cells = 0

            for page in doc.pages:
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                total_chars += len(text.strip())
                total_tables += len(tables)
                for t in tables:
                    total_table_cells += sum(len(row) for row in t if row)

            result.update({
                "total_chars": total_chars,
                "total_tables": total_tables,
                "total_table_cells": total_table_cells,
                "avg_tables_per_page": total_tables / max(len(doc.pages), 1),
            })
    except Exception as e:
        result["error"] = str(e)
    result["time_sec"] = round(time.time() - start, 4)
    return result


def analyze_pdf_characteristics(pdfs: list[Path]) -> dict:
    """Analyze characteristics of the PDF corpus."""
    stats = {
        "total": len(pdfs),
        "has_text": 0,
        "is_scanned": 0,
        "has_images": 0,
        "has_tables": 0,
        "page_counts": [],
        "char_counts": [],
        "time_pymupdf": [],
        "time_pdfplumber": [],
        "errors_pymupdf": 0,
        "errors_pdfplumber": 0,
    }

    scanned_examples = []
    table_examples = []
    text_examples = []

    print(f"\nBenchmarking {len(pdfs)} PDFs...")
    for pdf_path in tqdm(pdfs, desc="Processing"):
        mu = benchmark_pymupdf(pdf_path)
        pl = benchmark_pdfplumber(pdf_path)

        if mu.get("error"):
            stats["errors_pymupdf"] += 1
            continue
        if pl.get("error"):
            stats["errors_pdfplumber"] += 1

        stats["page_counts"].append(mu["page_count"])
        stats["char_counts"].append(mu["total_chars"])
        stats["time_pymupdf"].append(mu["time_sec"])
        if not pl.get("error"):
            stats["time_pdfplumber"].append(pl["time_sec"])

        if mu["has_text"]:
            stats["has_text"] += 1
            if len(text_examples) < 3:
                text_examples.append({
                    "file": pdf_path.name,
                    "chars": mu["total_chars"],
                    "pages": mu["page_count"],
                    "time_mu": mu["time_sec"],
                    "time_pl": pl.get("time_sec", 0),
                })
        if mu["is_scanned"]:
            stats["is_scanned"] += 1
            if len(scanned_examples) < 3:
                scanned_examples.append({
                    "file": pdf_path.name,
                    "pages": mu["page_count"],
                    "chars": mu["total_chars"],
                })
        if mu["total_images"] > 0:
            stats["has_images"] += 1
        if pl.get("total_tables", 0) > 0:
            stats["has_tables"] += 1
            if len(table_examples) < 3:
                table_examples.append({
                    "file": pdf_path.name,
                    "tables": pl["total_tables"],
                    "cells": pl["total_table_cells"],
                    "time_pl": pl.get("time_sec", 0),
                })

    stats["examples_text"] = text_examples
    stats["examples_scanned"] = scanned_examples
    stats["examples_tables"] = table_examples
    return stats


def print_report(stats: dict):
    total = stats["total"]
    print("\n" + "="*60)
    print("PDF CORPUS ANALYSIS REPORT")
    print("="*60)
    print(f"\nTotal PDFs analyzed: {total}")
    print(f"  Has text layer:  {stats['has_text']:3d} ({stats['has_text']/total*100:.1f}%)")
    print(f"  Scanned (no text): {stats['is_scanned']:3d} ({stats['is_scanned']/total*100:.1f}%)")
    print(f"  Has embedded images: {stats['has_images']:3d} ({stats['has_images']/total*100:.1f}%)")
    print(f"  Has tables (pdfplumber): {stats['has_tables']:3d} ({stats['has_tables']/total*100:.1f}%)")
    print(f"  Errors pymupdf:  {stats['errors_pymupdf']}")
    print(f"  Errors pdfplumber: {stats['errors_pdfplumber']}")

    if stats["page_counts"]:
        print(f"\nPage count stats:")
        print(f"  min={min(stats['page_counts'])}, max={max(stats['page_counts'])}, "
              f"avg={statistics.mean(stats['page_counts']):.1f}, "
              f"median={statistics.median(stats['page_counts']):.1f}")

    if stats["time_pymupdf"]:
        print(f"\nSpeed stats:")
        print(f"  PyMuPDF avg:     {statistics.mean(stats['time_pymupdf'])*1000:.1f}ms/file")
        print(f"  PyMuPDF median:  {statistics.median(stats['time_pymupdf'])*1000:.1f}ms/file")
    if stats["time_pdfplumber"]:
        print(f"  pdfplumber avg:  {statistics.mean(stats['time_pdfplumber'])*1000:.1f}ms/file")
        print(f"  pdfplumber median: {statistics.median(stats['time_pdfplumber'])*1000:.1f}ms/file")

    if stats["examples_text"]:
        print("\nText PDF examples (first 3):")
        for ex in stats["examples_text"]:
            print(f"  {ex['file']}: {ex['pages']}p, {ex['chars']} chars, "
                  f"mu={ex['time_mu']*1000:.0f}ms, pl={ex['time_pl']*1000:.0f}ms")

    if stats["examples_scanned"]:
        print("\nScanned PDF examples:")
        for ex in stats["examples_scanned"]:
            print(f"  {ex['file']}: {ex['pages']}p, {ex['chars']} chars (SCANNED)")

    if stats["examples_tables"]:
        print("\nTable-heavy PDF examples:")
        for ex in stats["examples_tables"]:
            print(f"  {ex['file']}: {ex['tables']} tables, {ex['cells']} cells, "
                  f"pl={ex['time_pl']*1000:.0f}ms")


def run_deep_analysis(pdf_path: Path):
    """Deep analysis on a single PDF — show extracted text/tables."""
    print(f"\n{'='*60}")
    print(f"DEEP ANALYSIS: {pdf_path.name}")
    print(f"{'='*60}")

    mu_result = benchmark_pymupdf(pdf_path)
    pl_result = benchmark_pdfplumber(pdf_path)

    print(f"\nPyMuPDF:")
    print(f"  pages={mu_result.get('page_count')}, chars={mu_result.get('total_chars')}, "
          f"images={mu_result.get('total_images')}, time={mu_result.get('time_sec')}s")
    print(f"  has_text={mu_result.get('has_text')}, is_scanned={mu_result.get('is_scanned')}")

    print(f"\npdfplumber:")
    print(f"  pages={pl_result.get('page_count')}, chars={pl_result.get('total_chars')}, "
          f"tables={pl_result.get('total_tables')}, time={pl_result.get('time_sec')}s")

    # Show actual text from page 0
    if mu_result.get("has_text"):
        doc = fitz.open(str(pdf_path))
        if doc.page_count > 0:
            page = doc[0]
            text = page.get_text("text").strip()
            print(f"\nPage 0 text (first 500 chars):")
            print(f"  {text[:500]!r}")
        doc.close()

    # Show tables from page 0
    if pl_result.get("total_tables", 0) > 0:
        with pdfplumber.open(str(pdf_path)) as doc:
            for page_idx, page in enumerate(doc.pages[:2]):
                tables = page.extract_tables()
                if tables:
                    print(f"\nPage {page_idx} table[0] (first 3 rows):")
                    for row in tables[0][:3]:
                        print(f"  {row}")
                    break


def main():
    print("=== PDF Benchmark for VPP AI Agent (Toàn's Task) ===")

    # Sample PDFs
    all_pdfs = sample_pdfs(n_per_task=3)
    print(f"Found {len(all_pdfs)} PDFs to benchmark")

    # Run benchmark
    stats = analyze_pdf_characteristics(all_pdfs)
    print_report(stats)

    # Save results
    result_path = RESULTS_DIR / "01_pdf_benchmark.json"
    # Remove non-serializable data
    save_stats = {k: v for k, v in stats.items()
                  if k not in ("page_counts", "char_counts", "time_pymupdf", "time_pdfplumber")}
    save_stats["page_count_summary"] = {
        "min": min(stats["page_counts"]) if stats["page_counts"] else 0,
        "max": max(stats["page_counts"]) if stats["page_counts"] else 0,
        "avg": statistics.mean(stats["page_counts"]) if stats["page_counts"] else 0,
    }
    save_stats["speed_ms"] = {
        "pymupdf_avg": statistics.mean(stats["time_pymupdf"]) * 1000 if stats["time_pymupdf"] else 0,
        "pdfplumber_avg": statistics.mean(stats["time_pdfplumber"]) * 1000 if stats["time_pdfplumber"] else 0,
    }
    with open(result_path, "w") as f:
        json.dump(save_stats, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {result_path}")

    # Deep analysis on 3 representative PDFs
    if all_pdfs:
        print("\n\n=== DEEP ANALYSIS on sample files ===")
        for pdf in all_pdfs[:3]:
            run_deep_analysis(pdf)


if __name__ == "__main__":
    main()
