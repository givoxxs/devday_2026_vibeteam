"""
Experiment 06: Test docling pipeline on a real scanned PDF.
Saves full detailed output to JSON + TXT log.

Run:
  # Auto-pick 1 scanned PDF
  conda run -n devday python experiments/toan/06_docling_test.py

  # Specific file
  conda run -n devday python experiments/toan/06_docling_test.py --pdf path/to/file.pdf

  # N files
  conda run -n devday python experiments/toan/06_docling_test.py --n 3
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
LOG_DIR = Path(__file__).parent / "sample_outputs" / "docling_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def find_sample_pdfs(n: int = 1) -> list[Path]:
    """Lấy scanned PDFs có kích thước lớn (nhiều nội dung)."""
    pdfs = []
    for task_dir in sorted(DATA_DIR.iterdir()):
        if not task_dir.name.startswith("task_"):
            continue
        for pdf in task_dir.rglob("*.pdf"):
            pdfs.append(pdf)
    pdfs.sort(key=lambda p: p.stat().st_size, reverse=True)
    return pdfs[:n]


def test_docling_single(pdf_path: Path) -> dict:
    """
    Chạy docling trên 1 PDF. Lưu full output vào log.
    """
    stem = pdf_path.stem[:20]
    log_path = LOG_DIR / f"{stem}_docling.txt"
    json_path = LOG_DIR / f"{stem}_docling.json"

    result = {
        "file": pdf_path.name,
        "path": str(pdf_path),
        "size_kb": pdf_path.stat().st_size // 1024,
        "error": None,
        "processing_time_sec": 0,
        "markdown_chars": 0,
        "table_count": 0,
        "picture_count": 0,
        "page_count": 0,
        "markdown_full": "",
        "tables": [],
        "pictures": [],
        "log_path": str(log_path),
        "json_path": str(json_path),
    }

    log_lines = [
        f"=== DOCLING TEST ===",
        f"File: {pdf_path.name}",
        f"Path: {pdf_path}",
        f"Size: {result['size_kb']} KB",
        "",
    ]

    start = time.time()
    try:
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        # Dùng OCR pipeline mặc định (RapidOCR trên macOS)
        pipeline_opts = PdfPipelineOptions(do_ocr=True)
        converter = DocumentConverter(
            format_options={
                "pdf": PdfFormatOption(pipeline_options=pipeline_opts)
            }
        )

        log_lines.append("Converting with docling (OCR enabled)...")
        conv_result = converter.convert(str(pdf_path))
        doc = conv_result.document

        # --- Page count ---
        result["page_count"] = conv_result.pages.__len__() if hasattr(conv_result, 'pages') else "?"

        # --- Full Markdown ---
        md = doc.export_to_markdown()
        result["markdown_full"] = md
        result["markdown_chars"] = len(md)

        log_lines += [
            f"",
            f"=== MARKDOWN OUTPUT ({len(md)} chars) ===",
            md,
            "",
        ]

        # --- Tables ---
        tables_data = []
        for i, table in enumerate(doc.tables):
            try:
                table_md = table.export_to_markdown()
                # Try to get structured data
                grid = None
                if hasattr(table, 'data') and hasattr(table.data, 'grid'):
                    grid = [[cell.text for cell in row] for row in table.data.grid]

                t = {
                    "index": i,
                    "markdown": table_md,
                    "rows": len(grid) if grid else "?",
                    "cols": len(grid[0]) if grid else "?",
                    "grid": grid,
                }
                tables_data.append(t)

                log_lines += [
                    f"=== TABLE {i+1} ({t['rows']} rows × {t['cols']} cols) ===",
                    table_md,
                    "",
                ]
            except Exception as e:
                tables_data.append({"index": i, "error": str(e)})

        result["table_count"] = len(tables_data)
        result["tables"] = tables_data

        # --- Pictures ---
        pictures_data = []
        for i, pic in enumerate(doc.pictures):
            try:
                p = {
                    "index": i,
                    "caption": str(pic.caption_text(doc)) if hasattr(pic, 'caption_text') else "",
                }
                pictures_data.append(p)
                log_lines.append(f"=== PICTURE {i+1}: {p['caption'][:100]} ===\n")
            except Exception as e:
                pictures_data.append({"index": i, "error": str(e)})

        result["picture_count"] = len(pictures_data)
        result["pictures"] = pictures_data

    except Exception as e:
        result["error"] = str(e)
        log_lines.append(f"ERROR: {e}")

    result["processing_time_sec"] = round(time.time() - start, 2)
    log_lines.insert(4, f"Processing time: {result['processing_time_sec']}s")

    # Save log TXT
    log_path.write_text("\n".join(log_lines), encoding="utf-8")

    # Save JSON (exclude full markdown from result dict to keep it clean)
    json_result = {k: v for k, v in result.items() if k != "markdown_full"}
    json_result["tables"] = [
        {k2: v2 for k2, v2 in t.items() if k2 != "grid"} for t in result["tables"]
    ]
    json_path.write_text(json.dumps(json_result, indent=2, ensure_ascii=False), encoding="utf-8")

    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf", default=None, help="Specific PDF path")
    parser.add_argument("--n", type=int, default=1, help="Number of sample PDFs")
    args = parser.parse_args()

    if args.pdf:
        pdf_paths = [Path(args.pdf)]
    else:
        print(f"Finding {args.n} large PDF(s) from data/...\n")
        pdf_paths = find_sample_pdfs(args.n)
        if not pdf_paths:
            print("No PDFs found.")
            return
        for p in pdf_paths:
            print(f"  → {p.name} ({p.stat().st_size//1024} KB)")
        print()

    all_results = []
    for pdf_path in pdf_paths:
        print(f"Processing: {pdf_path.name}")
        r = test_docling_single(pdf_path)

        if r["error"]:
            print(f"  ❌ ERROR: {r['error']}")
        else:
            print(f"  ✅ {r['processing_time_sec']}s | {r['markdown_chars']} chars | "
                  f"{r['table_count']} tables | {r['picture_count']} pictures")
            print(f"  Log: {r['log_path']}")
            print(f"  JSON: {r['json_path']}")
            print()
            print("--- Markdown preview (first 600 chars) ---")
            print(r["markdown_full"][:600])
            print("...")
            if r["tables"]:
                print(f"\n--- Table 1/{r['table_count']} ---")
                print(r["tables"][0]["markdown"][:400])
        all_results.append(r)
        print()

    # Summary JSON
    summary_path = RESULTS_DIR / "06_docling_test.json"
    summary = [{k: v for k, v in r.items() if k != "markdown_full"} for r in all_results]
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Summary saved: {summary_path}")


if __name__ == "__main__":
    main()
