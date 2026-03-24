"""
Experiment 02: Run full PDF pipeline on all tasks.
For each task, process all files and output:
- Extracted text, tables, images count
- Document type guess
- Processing stats

Run: conda run -n devday python experiments/toan/02_run_pipeline_on_tasks.py
"""
import json
import os
import sys
import time
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tqdm import tqdm
from src.document_processor import process_pdf, extract_dates, extract_numeric_values, detect_language, clean_text

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
SAMPLE_OUTPUT_DIR = Path(__file__).parent / "sample_outputs"
SAMPLE_OUTPUT_DIR.mkdir(exist_ok=True)


def load_task_info(task_dir: Path) -> dict:
    vi_path = task_dir / "task_info_vi.json"
    jp_path = task_dir / "task_info.json"
    vi = json.loads(vi_path.read_text()) if vi_path.exists() else {}
    jp = json.loads(jp_path.read_text()) if jp_path.exists() else {}
    return {**jp, "prompt_vi": vi.get("prompt_template", ""), "tags_vi": vi.get("tags_vi", [])}


def process_task(task_dir: Path) -> dict:
    """Process all files in a task, return summary."""
    task_info = load_task_info(task_dir)
    task_id = task_info.get("task_id", task_dir.name.replace("task_", ""))

    result = {
        "task_id": task_id,
        "prompt_vi": task_info.get("prompt_vi", ""),
        "tags_vi": task_info.get("tags_vi", []),
        "resource_count": task_info.get("resource_count", 0),
        "files": [],
        "stats": {
            "total_files": 0,
            "pdfs": 0,
            "xlsx": 0,
            "others": 0,
            "has_text": 0,
            "scanned": 0,
            "has_tables": 0,
            "has_images": 0,
            "total_chars": 0,
            "total_pages": 0,
            "total_processing_time": 0,
            "errors": 0,
        }
    }

    # Get all files for this task
    resources = task_info.get("resources_info", [])
    for res in resources:
        file_path = task_dir / res["file_path"]
        if not file_path.exists():
            continue

        file_type = res.get("file_type", "pdf")
        result["stats"]["total_files"] += 1

        if file_type == "pdf":
            result["stats"]["pdfs"] += 1
            doc = process_pdf(str(file_path), task_id=task_id, extract_images=False)

            if doc.error:
                result["stats"]["errors"] += 1
                result["files"].append({
                    "file": file_path.name,
                    "type": "pdf",
                    "error": doc.error,
                })
                continue

            # Post-processing: extract entities
            dates = extract_dates(doc.full_text)
            nums = extract_numeric_values(doc.full_text)
            langs = detect_language(doc.full_text[:500])

            file_summary = {
                "file": file_path.name,
                "type": "pdf",
                "pages": doc.page_count,
                "chars": len(doc.full_text),
                "has_text": doc.has_text_layer,
                "is_scanned": doc.is_scanned,
                "has_tables": any(
                    e.__class__.__name__ == "TableElement"
                    for page in doc.pages
                    for e in page.elements
                ),
                "has_images": any(
                    e.__class__.__name__ == "ImageElement"
                    for page in doc.pages
                    for e in page.elements
                ),
                "dates_found": dates[:3],
                "numeric_values": {k: v[:2] for k, v in nums.items()},
                "languages": langs,
                "text_preview": clean_text(doc.full_text)[:200] if doc.full_text else "",
                "processing_time_sec": doc.processing_time_sec,
            }
            result["files"].append(file_summary)

            # Update stats
            if doc.has_text_layer:
                result["stats"]["has_text"] += 1
            if doc.is_scanned:
                result["stats"]["scanned"] += 1
            if file_summary["has_tables"]:
                result["stats"]["has_tables"] += 1
            if file_summary["has_images"]:
                result["stats"]["has_images"] += 1
            result["stats"]["total_chars"] += len(doc.full_text)
            result["stats"]["total_pages"] += doc.page_count
            result["stats"]["total_processing_time"] += doc.processing_time_sec

        elif file_type in ("xlsx", "xls"):
            result["stats"]["xlsx"] += 1
            try:
                import pandas as pd
                sheets = pd.read_excel(str(file_path), sheet_name=None, nrows=10)
                sheet_summary = {sheet: df.to_csv(index=False)[:200] for sheet, df in sheets.items()}
                result["files"].append({
                    "file": file_path.name,
                    "type": "xlsx",
                    "sheets": list(sheets.keys()),
                    "preview": sheet_summary,
                })
            except Exception as e:
                result["files"].append({"file": file_path.name, "type": "xlsx", "error": str(e)})

        elif file_type in ("docx", "doc"):
            result["stats"]["others"] += 1
            try:
                import docx
                d = docx.Document(str(file_path))
                text = "\n".join(p.text for p in d.paragraphs if p.text.strip())
                result["files"].append({
                    "file": file_path.name,
                    "type": file_type,
                    "chars": len(text),
                    "text_preview": text[:200],
                })
            except Exception as e:
                result["files"].append({"file": file_path.name, "type": file_type, "error": str(e)})
        else:
            result["stats"]["others"] += 1

    return result


def main():
    print("=== Pipeline Run on All Tasks ===\n")

    task_dirs = sorted([d for d in DATA_DIR.iterdir() if d.is_dir() and d.name.startswith("task_")])
    print(f"Found {len(task_dirs)} tasks")

    all_results = []
    aggregate = defaultdict(int)

    for task_dir in tqdm(task_dirs, desc="Tasks"):
        result = process_task(task_dir)
        all_results.append(result)

        s = result["stats"]
        aggregate["total_files"] += s["total_files"]
        aggregate["pdfs"] += s["pdfs"]
        aggregate["has_text"] += s["has_text"]
        aggregate["scanned"] += s["scanned"]
        aggregate["has_tables"] += s["has_tables"]
        aggregate["has_images"] += s["has_images"]
        aggregate["total_chars"] += s["total_chars"]
        aggregate["total_pages"] += s["total_pages"]
        aggregate["total_time"] += s["total_processing_time"]
        aggregate["errors"] += s["errors"]

    # ── Print summary ─────────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("PIPELINE RUN SUMMARY")
    print("="*60)
    print(f"Tasks processed:   {len(task_dirs)}")
    print(f"Total files:       {aggregate['total_files']}")
    print(f"PDFs processed:    {aggregate['pdfs']}")
    print(f"  Has text layer:  {aggregate['has_text']} ({aggregate['has_text']/max(aggregate['pdfs'],1)*100:.1f}%)")
    print(f"  Scanned:         {aggregate['scanned']} ({aggregate['scanned']/max(aggregate['pdfs'],1)*100:.1f}%)")
    print(f"  Has tables:      {aggregate['has_tables']} ({aggregate['has_tables']/max(aggregate['pdfs'],1)*100:.1f}%)")
    print(f"  Has images:      {aggregate['has_images']} ({aggregate['has_images']/max(aggregate['pdfs'],1)*100:.1f}%)")
    print(f"Total pages:       {aggregate['total_pages']}")
    print(f"Total chars:       {aggregate['total_chars']:,}")
    print(f"Avg chars/file:    {aggregate['total_chars']//max(aggregate['pdfs'],1):,}")
    print(f"Total proc time:   {aggregate['total_time']:.2f}s")
    print(f"Avg time/file:     {aggregate['total_time']/max(aggregate['pdfs'],1)*1000:.1f}ms")
    print(f"Errors:            {aggregate['errors']}")

    # ── Per-task summary ──────────────────────────────────────────────────────
    print("\n\nPER-TASK SUMMARY:")
    print(f"{'Task':10} {'#Files':7} {'#Scanned':9} {'#Tables':8} {'TotalChars':11} {'Time(s)':8} Tags")
    print("-"*80)
    for r in all_results:
        s = r["stats"]
        tags = ", ".join(r["tags_vi"])[:40]
        print(f"{r['task_id'][:8]:10} {s['total_files']:7} {s['scanned']:9} "
              f"{s['has_tables']:8} {s['total_chars']:11,} {s['total_processing_time']:8.2f} {tags}")

    # ── Save results ──────────────────────────────────────────────────────────
    out_path = RESULTS_DIR / "02_pipeline_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "aggregate": dict(aggregate),
            "tasks": all_results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nFull results saved to {out_path}")

    # ── Save detailed sample for 5 QA tasks ──────────────────────────────────
    qa_tasks = [r for r in all_results if "sắp xếp vào thư mục" not in r["prompt_vi"]][:5]
    for r in qa_tasks:
        sample_path = SAMPLE_OUTPUT_DIR / f"task_{r['task_id'][:8]}_detail.json"
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump(r, f, indent=2, ensure_ascii=False)
    print(f"Sample outputs saved to {SAMPLE_OUTPUT_DIR}")

    # ── Highlight scanned PDFs ────────────────────────────────────────────────
    scanned_files = []
    for r in all_results:
        for f in r["files"]:
            if f.get("is_scanned"):
                scanned_files.append({
                    "task": r["task_id"][:8],
                    "file": f["file"],
                    "pages": f.get("pages", 0),
                })
    if scanned_files:
        print(f"\n\nSCANNED PDFs ({len(scanned_files)} total — need Vision LLM):")
        for sf in scanned_files[:20]:
            print(f"  task_{sf['task']}: {sf['file']} ({sf['pages']} pages)")

    # ── Highlight table-heavy files ───────────────────────────────────────────
    table_files = []
    for r in all_results:
        for f in r["files"]:
            if f.get("has_tables"):
                table_files.append({
                    "task": r["task_id"][:8],
                    "file": f["file"],
                    "tag": r["tags_vi"],
                })
    print(f"\n\nFILES WITH TABLES ({len(table_files)} total):")
    for tf in table_files[:15]:
        print(f"  task_{tf['task']}: {tf['file']} | tags={tf['tag']}")


if __name__ == "__main__":
    main()
