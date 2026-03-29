"""
Experiment 02: Run full PDF pipeline on all tasks (or a single task).

Usage:
  # All tasks, no Vision LLM (fast benchmark)
  conda run -n devday python experiments/toan/02_run_pipeline_on_tasks.py

  # Single task
  conda run -n devday python experiments/toan/02_run_pipeline_on_tasks.py --task 328e47b5

  # Single task WITH Vision LLM + log file
  conda run -n devday python experiments/toan/02_run_pipeline_on_tasks.py --task 328e47b5 --vision --log
"""
import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tqdm import tqdm
from src.document_processor import process_pdf, extract_dates, extract_numeric_values, clean_text
from src.document_processor.image_processor import process_image_file

IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "tiff", "tif", "bmp", "gif", "webp"}

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
SAMPLE_OUTPUT_DIR = Path(__file__).parent / "sample_outputs"
SAMPLE_OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)


def setup_logger(task_id: str) -> logging.Logger:
    """Set up file + console logger for a task run."""
    log_file = LOGS_DIR / f"{task_id}.log"
    logger = logging.getLogger(f"pipeline.{task_id}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger, log_file


def load_task_info(task_dir: Path) -> dict:
    vi_path = task_dir / "task_info_vi.json"
    jp_path = task_dir / "task_info.json"
    vi = json.loads(vi_path.read_text()) if vi_path.exists() else {}
    jp = json.loads(jp_path.read_text()) if jp_path.exists() else {}
    return {**jp, "prompt_vi": vi.get("prompt_template", ""), "tags_vi": vi.get("tags_vi", [])}


def process_task(task_dir: Path, use_vision_llm: bool = False, logger=None) -> dict:
    """Process all files in a task, return summary."""
    log = logger.info if logger else print

    task_info = load_task_info(task_dir)
    task_id = task_info.get("task_id", task_dir.name.replace("task_", ""))

    log(f"{'='*60}")
    log(f"TASK: {task_id}")
    log(f"Tags: {task_info.get('tags_vi', [])}")
    log(f"Prompt: {task_info.get('prompt_vi', '')[:120]}")
    log(f"{'='*60}")

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
            "images": 0,
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
            if logger:
                logger.warning(f"  MISSING: {res['file_path']}")
            continue

        file_type = res.get("file_type", "pdf")
        result["stats"]["total_files"] += 1
        log(f"  Processing [{file_type.upper()}] {file_path.name} ({file_path.stat().st_size // 1024} KB)")

        if file_type == "pdf":
            result["stats"]["pdfs"] += 1
            doc = process_pdf(str(file_path), task_id=task_id, extract_images=False, use_vision_llm=use_vision_llm)

            if doc.error:
                result["stats"]["errors"] += 1
                result["files"].append({
                    "file": file_path.name,
                    "type": "pdf",
                    "error": doc.error,
                })
                if logger:
                    logger.error(f"    ERROR: {doc.error}")
                continue

            scan_label = "SCANNED" if doc.is_scanned else "TEXT"
            log(f"    [{scan_label}] pages={doc.page_count} chars={len(doc.full_text)} time={doc.processing_time_sec}s method={doc.processing_method}")

            # Post-processing: extract entities
            dates = extract_dates(doc.full_text)
            nums = extract_numeric_values(doc.full_text)

            has_tables = (
                any(e.__class__.__name__ == "TableElement" for page in doc.pages for e in page.elements)
                or any("|" in (page.ocr_text or "") for page in doc.pages)
            )
            has_images = (
                any(e.__class__.__name__ == "ImageElement" for page in doc.pages for e in page.elements)
                or any("[IMAGE:" in (page.ocr_text or "") for page in doc.pages)
            )

            log(f"    doc_type={doc.document_type_guess or 'unknown'} | folder={doc.folder_candidate} ({doc.folder_confidence:.2f}) | tables={has_tables} images={has_images}")
            if dates:
                log(f"    dates={dates[:3]}")
            if doc.full_text:
                log(f"    preview: {clean_text(doc.full_text)[:150]}")

            pages_detail = []
            for page in doc.pages:
                texts  = [e for e in page.elements if e.__class__.__name__ == "TextElement"]
                tables = [e for e in page.elements if e.__class__.__name__ == "TableElement"]
                images = [e for e in page.elements if e.__class__.__name__ == "ImageElement"]
                # For text PDFs, build ocr_text from TextElements if page.ocr_text is empty
                page_ocr = page.ocr_text
                if not page_ocr and texts:
                    page_ocr = " ".join(t.content for t in texts)[:500]

                pages_detail.append({
                    "page_index": page.page_index,
                    "ocr_text": page_ocr,
                    "text_elements": len(texts),
                    "table_elements": len(tables),
                    "image_elements": len(images),
                    "sample_text": texts[0].content[:100] if texts else None,
                    "tables": [{"rows": t.num_rows, "cols": t.num_cols, "preview": t.content[:100]} for t in tables],
                    "images": [{"width": i.width, "height": i.height, "caption": i.caption} for i in images],
                })

            file_summary = {
                "file": file_path.name,
                "type": "pdf",
                "pages": doc.page_count,
                "chars": len(doc.full_text),
                "has_text": doc.has_text_layer,
                "is_scanned": doc.is_scanned,
                "processing_method": doc.processing_method,
                "document_type": doc.document_type_guess,
                "folder_candidate": doc.folder_candidate,
                "folder_confidence": doc.folder_confidence,
                "has_tables": has_tables,
                "has_images": has_images,
                "dates_found": dates[:3],
                "numeric_values": {k: v[:2] for k, v in nums.items()},
                "text_preview": clean_text(doc.full_text)[:200] if doc.full_text else "",
                "processing_time_sec": doc.processing_time_sec,
                "pages_detail": pages_detail,
            }
            result["files"].append(file_summary)

            # Update stats
            if doc.has_text_layer:
                result["stats"]["has_text"] += 1
            if doc.is_scanned:
                result["stats"]["scanned"] += 1
            if has_tables:
                result["stats"]["has_tables"] += 1
            if has_images:
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
                log(f"    sheets={list(sheets.keys())}")
            except Exception as e:
                result["files"].append({"file": file_path.name, "type": "xlsx", "error": str(e)})
                if logger:
                    logger.error(f"    ERROR: {e}")

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
                log(f"    chars={len(text)}")
            except Exception as e:
                result["files"].append({"file": file_path.name, "type": file_type, "error": str(e)})
                if logger:
                    logger.error(f"    ERROR: {e}")

        elif file_type in IMAGE_EXTENSIONS:
            result["stats"]["images"] += 1
            img_doc = process_image_file(
                str(file_path),
                task_id=task_id,
                use_vision_llm=use_vision_llm,
            )
            if img_doc.error:
                result["stats"]["errors"] += 1
                result["files"].append({
                    "file": file_path.name,
                    "type": file_type,
                    "error": img_doc.error,
                })
                if logger:
                    logger.error(f"    ERROR: {img_doc.error}")
            else:
                result["files"].append({
                    "file": file_path.name,
                    "type": file_type,
                    "content_type": img_doc.content_type.value if img_doc.content_type else None,
                    "document_type": img_doc.document_type_guess,
                    "folder_candidate": img_doc.folder_candidate,
                    "folder_confidence": img_doc.folder_confidence,
                    "caption": img_doc.image_caption,
                    "text_preview": img_doc.full_text[:200] if img_doc.full_text else "",
                    "processing_time_sec": img_doc.processing_time_sec,
                })
                log(f"    content_type={img_doc.content_type} folder={img_doc.folder_candidate} caption={str(img_doc.image_caption)[:80]}")

        else:
            result["stats"]["others"] += 1
            log(f"    (skipped — unsupported type)")

    s = result["stats"]
    log(f"  DONE: {s['total_files']} files | {s['pdfs']} PDFs ({s['scanned']} scanned) | errors={s['errors']} | time={s['total_processing_time']:.2f}s")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", default=None, help="Run only task matching this prefix")
    parser.add_argument("--vision", action="store_true", help="Enable Vision LLM for scanned PDFs")
    parser.add_argument("--log", action="store_true", help="Write detailed log to logs/<task_id>.log")
    args = parser.parse_args()

    all_task_dirs = sorted([d for d in DATA_DIR.iterdir() if d.is_dir() and d.name.startswith("task_")])

    if args.task:
        task_dirs = [d for d in all_task_dirs if args.task in d.name]
        if not task_dirs:
            print(f"No task matching '{args.task}'. Available: {[d.name[5:13] for d in all_task_dirs[:5]]}...")
            return
        print(f"=== Pipeline Run — task {task_dirs[0].name} | Vision={'ON' if args.vision else 'OFF'} ===\n")
    else:
        task_dirs = all_task_dirs
        print(f"=== Pipeline Run — {len(task_dirs)} tasks | Vision={'ON' if args.vision else 'OFF'} ===\n")

    all_results = []
    aggregate = defaultdict(int)

    for task_dir in tqdm(task_dirs, desc="Tasks"):
        logger, log_file = setup_logger(task_dir.name) if args.log else (None, None)
        if log_file:
            tqdm.write(f"  Log: {log_file}")
        result = process_task(task_dir, use_vision_llm=args.vision, logger=logger)
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

    # ── Single task: detailed file-by-file output ─────────────────────────────
    if args.task and all_results:
        r = all_results[0]
        print(f"\n{'='*60}")
        print(f"TASK: {r['task_id']}")
        print(f"Tags:   {r['tags_vi']}")
        print(f"Prompt: {r['prompt_vi'][:100]}...")
        print(f"{'='*60}\n")
        for f in r["files"]:
            if f.get("error"):
                print(f"  ❌  {f['file']} — {f['error'][:80]}")
            elif f["type"] == "pdf":
                scan  = "SCANNED" if f.get("is_scanned") else "TEXT  "
                dtype = f.get("document_type") or "unknown"
                fnum  = f.get("folder_candidate")
                fconf = f.get("folder_confidence", 0)
                folder_str = f"folder={fnum} ({fconf:.2f})" if fnum else "folder=?"
                print(f"  📄  {f['file']}")
                print(f"      [{scan}] p={f['pages']} chars={f['chars']}")
                print(f"      type={dtype} | {folder_str} | tables={f['has_tables']} images={f['has_images']}")
                if f.get("dates_found"):
                    print(f"      dates={f['dates_found']}")
                if f.get("text_preview"):
                    print(f"      preview: {f['text_preview'][:120]}")
            elif f["type"] in IMAGE_EXTENSIONS:
                fnum  = f.get("folder_candidate")
                fconf = f.get("folder_confidence", 0)
                folder_str = f"folder={fnum} ({fconf:.2f})" if fnum else "folder=?"
                dtype = f.get("document_type") or "unknown"
                print(f"  🖼️   {f['file']}")
                print(f"      content_type={f.get('content_type')} | type={dtype} | {folder_str}")
                if f.get("caption"):
                    print(f"      caption: {f['caption'][:120]}")
            else:
                print(f"  📊  {f['file']} [{f['type']}]")
            print()

        # Save JSON result for single task
        task_short = r["task_id"][:8]
        vision_suffix = "_vision" if args.vision else ""
        json_path = RESULTS_DIR / f"task_{task_short}{vision_suffix}.json"
        json_path.write_text(json.dumps(r, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Result saved: {json_path}")
        return

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
