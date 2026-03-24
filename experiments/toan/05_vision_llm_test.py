"""
Experiment 05: Vision LLM (GPT-4o) on scanned PDFs.
- Render scanned PDF pages to PNG
- Call GPT-4o vision to extract: document_type, folder_number, key_info, text
- Measure accuracy vs ground truth tags
- Measure latency and token cost
- Test batch (multi-page) vs single-page calls

Run: conda run -n devday python experiments/toan/05_vision_llm_test.py
"""
import asyncio
import base64
import io
import json
import os
import sys
import time
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import fitz
from PIL import Image
from openai import AsyncOpenAI
# Load API key
env_path = Path(__file__).parent.parent.parent / ".env"
api_key = None
if env_path.exists():
    for line in env_path.read_text().strip().splitlines():
        if line.startswith("OPENAI_KEY="):
            api_key = line.split("=", 1)[1].strip()
            break
if not api_key:
    api_key = os.environ.get("OPENAI_API_KEY", "")

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

VISION_MODEL = "gpt-4o"
DPI = 150  # render resolution

# ── Folder rules summary (for prompt context) ─────────────────────────────────
FOLDER_RULES = """
VPP solar project document folders:
1=Spine/Cover, 2=Table of Contents, 3=Equipment Handover List, 4=Completion Report,
5=Construction Schedule, 6=As-built Drawings, 7=Test Reports/Inspection Sheets,
8=Self-Inspection Sheets, 10=Equipment Config/List, 11=PCS/Power Conditioners,
12=Modules, 13=Monitoring/Communication Devices, 14=Equipment Specs,
15=User/Operation Manuals, 16=Administrative Documents, 17=Utility Documents/Responses,
18=Warranties, 19=Construction Photos/Album, 20=Strength Calculation Documents,
22=Other/Manifests
"""

PROMPT_SINGLE_PAGE = f"""You are analyzing a scanned document from a Japanese solar power plant (VPP) construction project.

{FOLDER_RULES}

Analyze this document page and respond ONLY with valid JSON (no markdown, no extra text):
{{
  "document_type": "<English name of document type>",
  "document_type_jp": "<Japanese name if visible>",
  "folder_number": <integer 1-22>,
  "folder_confidence": <float 0.0-1.0>,
  "language": "<ja|en|mixed>",
  "key_info": ["<fact1>", "<fact2>", "<fact3>"],
  "dates": ["<date1>"],
  "equipment": ["<name1>"],
  "numeric_values": {{"<label>": "<value>"}},
  "text_summary": "<1-2 sentence summary of document content>",
  "ocr_sample": "<first 200 chars of main text in document>"
}}"""


def render_pdf_page_b64(pdf_path: str, page_idx: int = 0, dpi: int = DPI) -> str | None:
    """Render a PDF page to base64 PNG string."""
    try:
        doc = fitz.open(pdf_path)
        if page_idx >= doc.page_count:
            doc.close()
            return None
        page = doc[page_idx]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        doc.close()
        return base64.b64encode(img_bytes).decode("utf-8")
    except Exception as e:
        print(f"  Render error {pdf_path}: {e}")
        return None


async def call_vision_llm(client: AsyncOpenAI, img_b64: str, prompt: str) -> dict:
    """Call GPT-4o with a single image."""
    start = time.time()
    try:
        resp = await client.chat.completions.create(
            model=VISION_MODEL,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/png;base64,{img_b64}",
                        "detail": "high"
                    }},
                    {"type": "text", "text": prompt},
                ]
            }],
            max_tokens=600,
            temperature=0,
        )
        elapsed = time.time() - start
        content = resp.choices[0].message.content.strip()
        # Clean markdown code fences if any
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        parsed = json.loads(content)
        return {
            "success": True,
            "result": parsed,
            "latency_sec": round(elapsed, 2),
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
        }
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON parse error: {e}", "raw": content[:200], "latency_sec": round(time.time()-start, 2)}
    except Exception as e:
        return {"success": False, "error": str(e), "latency_sec": round(time.time()-start, 2)}


def load_test_files(n_per_tag: int = 2) -> list[dict]:
    """Get representative files from each tag group."""
    test_files = []
    tag_seen = defaultdict(int)

    for task_dir in sorted(DATA_DIR.iterdir()):
        if not task_dir.is_dir():
            continue
        vi_path = task_dir / "task_info_vi.json"
        if not vi_path.exists():
            continue
        vi = json.loads(vi_path.read_text())
        tags = vi.get("tags_vi", [])
        resources = vi.get("resources_info", [])

        for res in resources:
            file_path = task_dir / res["file_path"]
            if not file_path.exists() or res.get("file_type") != "pdf":
                continue

            # Check if scanned (quick check)
            try:
                doc = fitz.open(str(file_path))
                chars = sum(len(doc[i].get_text("text").strip()) for i in range(min(2, doc.page_count)))
                doc.close()
                if chars > 100:  # has text — skip for this test
                    continue
            except:
                continue

            for tag in tags:
                if tag_seen[tag] < n_per_tag:
                    test_files.append({
                        "path": str(file_path),
                        "name": file_path.name,
                        "task_id": vi["task_id"][:8],
                        "tags": tags,
                        "tag_primary": tag,
                    })
                    tag_seen[tag] += 1
                    break

    return test_files


async def run_vision_tests(test_files: list[dict]) -> list[dict]:
    """Run Vision LLM on all test files with concurrency limit."""
    client = AsyncOpenAI(api_key=api_key)
    semaphore = asyncio.Semaphore(5)  # max 5 concurrent calls

    async def process_one(item: dict) -> dict:
        async with semaphore:
            img_b64 = render_pdf_page_b64(item["path"])
            if img_b64 is None:
                return {**item, "vision_result": None, "error": "render failed"}

            llm_result = await call_vision_llm(client, img_b64, PROMPT_SINGLE_PAGE)
            return {**item, **llm_result}

    print(f"Running Vision LLM on {len(test_files)} files (max 5 concurrent)...")
    tasks = [process_one(f) for f in test_files]
    results = []
    for coro in asyncio.as_completed(tasks):
        r = await coro
        tag = r.get("tag_primary", "?")[:35]
        if r.get("success"):
            pred = r.get("result", {})
            folder_pred = pred.get("folder_number", "?")
            folder_conf = pred.get("folder_confidence", 0)
            doc_type = pred.get("document_type", "?")[:30]
            latency = r.get("latency_sec", 0)
            print(f"  ✓ {r['name'][:35]:35s} | folder={folder_pred} ({folder_conf:.2f}) | {doc_type:30s} | {latency:.1f}s | tag={tag}")
        else:
            print(f"  ✗ {r['name'][:35]:35s} | ERROR: {r.get('error','?')[:50]}")
        results.append(r)

    await client.close()
    return results


def evaluate_accuracy(results: list[dict]) -> dict:
    """Evaluate folder prediction accuracy vs ground truth tags."""
    # Map tag string to folder number
    TAG_TO_FOLDER = {
        "01": 1, "02": 2, "03": 3, "04": 4, "05": 5,
        "06": 6, "07": 7, "08": 8, "10": 10, "11": 11,
        "12": 12, "13": 13, "14": 14, "15": 15, "16": 16,
        "17": 17, "18": 18, "19": 19, "20": 20, "22": 22,
    }

    correct = 0
    total = 0
    errors = 0
    per_tag = defaultdict(lambda: {"correct": 0, "total": 0, "predictions": []})

    for r in results:
        if not r.get("success"):
            errors += 1
            continue
        pred_folder = r.get("result", {}).get("folder_number")
        tags = r.get("tags", [])

        # Extract expected folder numbers from tags
        expected_folders = set()
        for tag in tags:
            # tag format: "07. Phieu ket qua..."
            num = tag.split(".")[0].strip()
            if num in TAG_TO_FOLDER:
                expected_folders.add(TAG_TO_FOLDER[num])
            elif num.isdigit():
                expected_folders.add(int(num))

        if not expected_folders:
            continue

        total += 1
        tag_key = r.get("tag_primary", "?")[:40]
        per_tag[tag_key]["total"] += 1
        per_tag[tag_key]["predictions"].append(pred_folder)

        if pred_folder in expected_folders:
            correct += 1
            per_tag[tag_key]["correct"] += 1

    accuracy = correct / total if total > 0 else 0
    return {
        "total": total,
        "correct": correct,
        "errors": errors,
        "accuracy": round(accuracy, 3),
        "per_tag": dict(per_tag),
    }


def print_report(results: list[dict], accuracy: dict):
    print("\n" + "="*70)
    print("VISION LLM TEST REPORT")
    print("="*70)

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    print(f"\nTotal tested:  {len(results)}")
    print(f"Successful:    {len(successful)}")
    print(f"Failed:        {len(failed)}")

    if successful:
        latencies = [r["latency_sec"] for r in successful]
        import statistics
        print(f"\nLatency (Vision LLM per page):")
        print(f"  avg:    {statistics.mean(latencies):.2f}s")
        print(f"  median: {statistics.median(latencies):.2f}s")
        print(f"  min:    {min(latencies):.2f}s")
        print(f"  max:    {max(latencies):.2f}s")

        in_tokens = [r.get("input_tokens", 0) for r in successful]
        out_tokens = [r.get("output_tokens", 0) for r in successful]
        print(f"\nToken usage (avg per call):")
        print(f"  input:  {sum(in_tokens)//len(in_tokens):,} tokens")
        print(f"  output: {sum(out_tokens)//len(out_tokens):,} tokens")
        # GPT-4o pricing: input $2.50/1M, output $10/1M
        total_cost = sum(in_tokens) * 2.5/1e6 + sum(out_tokens) * 10/1e6
        print(f"  total cost (this run): ${total_cost:.4f}")
        cost_per_file = total_cost / len(successful)
        print(f"  est. cost/file: ${cost_per_file:.4f}")

    print(f"\nAccuracy (folder prediction):")
    print(f"  Overall: {accuracy['correct']}/{accuracy['total']} = {accuracy['accuracy']*100:.1f}%")
    print(f"\nPer tag breakdown:")
    for tag, stats in sorted(accuracy["per_tag"].items()):
        acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        preds = stats["predictions"]
        print(f"  {tag[:40]:40s}: {stats['correct']}/{stats['total']} ({acc*100:.0f}%) | preds={preds}")

    if failed:
        print(f"\nFailed calls:")
        for r in failed[:5]:
            print(f"  {r['name']}: {r.get('error','?')[:60]}")

    # Sample successful results
    print(f"\nSample predictions:")
    for r in successful[:5]:
        pred = r.get("result", {})
        print(f"\n  File: {r['name']}")
        print(f"  Ground truth tags: {r['tags']}")
        print(f"  Predicted folder:  {pred.get('folder_number')} ({pred.get('folder_confidence', 0):.2f})")
        print(f"  Document type:     {pred.get('document_type')}")
        print(f"  Key info:          {pred.get('key_info', [])}")
        print(f"  OCR sample:        {str(pred.get('ocr_sample',''))[:100]}")


async def main():
    print("=== Vision LLM Test on Scanned PDFs ===\n")

    # Load test files
    test_files = load_test_files(n_per_tag=2)
    print(f"Test files selected: {len(test_files)}")
    for f in test_files:
        print(f"  {f['name'][:40]:40s} | tags={f['tags']}")

    if not test_files:
        print("No scanned test files found!")
        return

    print()

    # Run Vision LLM
    results = await run_vision_tests(test_files)

    # Evaluate
    accuracy = evaluate_accuracy(results)

    # Print report
    print_report(results, accuracy)

    # Save
    out_path = RESULTS_DIR / "05_vision_llm_results.json"
    save_results = []
    for r in results:
        save_results.append({k: v for k, v in r.items() if k != "img_b64"})
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"accuracy": accuracy, "results": save_results}, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
