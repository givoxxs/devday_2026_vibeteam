"""
Experiment 04: Render scanned PDFs to images + analyze image properties.
Key question: What do scanned PDFs look like? Are they photos, drawings, or tables?

Run: conda run -n devday python experiments/toan/04_scanned_pdf_render.py
"""
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import fitz
from PIL import Image

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
SAMPLE_OUTPUT_DIR = Path(__file__).parent / "sample_outputs" / "rendered_pages"
SAMPLE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def render_pdf_first_page(pdf_path: Path, output_path: Path, dpi: int = 150) -> dict:
    """Render first page of a PDF and analyze the image."""
    result = {"pdf": pdf_path.name, "error": None}
    try:
        doc = fitz.open(str(pdf_path))
        if doc.page_count == 0:
            result["error"] = "No pages"
            doc.close()
            return result

        page = doc[0]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        # Save PNG
        pix.save(str(output_path))

        # Analyze image
        img = Image.open(str(output_path))
        w, h = img.size
        gray = img.convert("L")
        pixels = list(gray.getdata())

        import statistics
        mean_val = statistics.mean(pixels)
        std_val = statistics.stdev(pixels)

        # Count dark pixels (potential text/lines)
        dark_pixels = sum(1 for p in pixels if p < 50)
        dark_ratio = dark_pixels / len(pixels)

        # Count light pixels (white background)
        light_pixels = sum(1 for p in pixels if p > 200)
        light_ratio = light_pixels / len(pixels)

        # Classify image type heuristically
        if light_ratio > 0.7 and dark_ratio < 0.1:
            img_type = "document/form"  # Mostly white with some dark text
        elif light_ratio > 0.5 and dark_ratio > 0.05:
            img_type = "drawing/diagram"
        elif mean_val < 128:
            img_type = "dark/technical"
        else:
            img_type = "photo/mixed"

        result.update({
            "pages": doc.page_count,
            "page_w": page.rect.width,
            "page_h": page.rect.height,
            "img_w": w,
            "img_h": h,
            "mean_brightness": round(mean_val, 1),
            "std_brightness": round(std_val, 1),
            "dark_pixel_ratio": round(dark_ratio, 3),
            "light_pixel_ratio": round(light_ratio, 3),
            "heuristic_type": img_type,
            "rendered_path": str(output_path),
        })
        doc.close()
    except Exception as e:
        result["error"] = str(e)
    return result


def main():
    print("=== Scanned PDF Render & Analysis ===\n")

    # Get scanned PDFs (load from pipeline results)
    pipeline_results_path = RESULTS_DIR / "02_pipeline_results.json"
    if not pipeline_results_path.exists():
        print("Run 02_run_pipeline_on_tasks.py first!")
        return

    with open(pipeline_results_path) as f:
        pipeline_data = json.load(f)

    # Collect scanned PDFs from tasks
    scanned_files = []
    for task in pipeline_data["tasks"]:
        task_dir = DATA_DIR / f"task_{task['task_id']}"
        if not task_dir.exists():
            # Try without "task_" prefix issue
            for d in DATA_DIR.iterdir():
                if task['task_id'] in d.name:
                    task_dir = d
                    break

        for file_info in task.get("files", []):
            if file_info.get("is_scanned") and file_info.get("type") == "pdf":
                # Find actual file path
                for res in task.get("files", []):
                    pass
                scanned_files.append({
                    "task_id": task["task_id"],
                    "task_dir": str(task_dir),
                    "file_name": file_info["file"],
                    "tags": task.get("tags_vi", []),
                })
                if len(scanned_files) >= 30:
                    break
        if len(scanned_files) >= 30:
            break

    # Find actual file paths for scanned PDFs
    rendered_results = []
    found_count = 0
    for item in scanned_files[:20]:
        task_dir = Path(item["task_dir"])
        # Search for the file
        matches = list(task_dir.rglob(item["file_name"]))
        if not matches:
            continue

        pdf_path = matches[0]
        output_path = SAMPLE_OUTPUT_DIR / f"task_{item['task_id'][:8]}_{item['file_name'].replace('.pdf', '')}_p0.png"

        result = render_pdf_first_page(pdf_path, output_path)
        result["tags"] = item["tags"]
        result["task_id"] = item["task_id"][:8]
        rendered_results.append(result)
        found_count += 1

        if result.get("error"):
            print(f"  ERROR {item['file_name']}: {result['error']}")
        else:
            print(f"  {item['file_name'][:40]:40s} | type={result['heuristic_type']:20s} | "
                  f"bright={result['mean_brightness']:5.1f} | dark={result['dark_pixel_ratio']:.3f} | "
                  f"tags={item['tags']}")

    print(f"\nRendered {found_count} pages to {SAMPLE_OUTPUT_DIR}")

    # Summary by heuristic type
    if rendered_results:
        valid = [r for r in rendered_results if not r.get("error")]
        type_counts = Counter(r["heuristic_type"] for r in valid)
        print(f"\nImage type distribution ({len(valid)} files):")
        for t, c in type_counts.most_common():
            print(f"  {t}: {c} ({c/len(valid)*100:.1f}%)")

        # By tag
        print("\nImage type by tag:")
        tag_types = {}
        for r in valid:
            for tag in r.get("tags", ["unknown"]):
                tag_short = tag[:30]
                if tag_short not in tag_types:
                    tag_types[tag_short] = Counter()
                tag_types[tag_short][r["heuristic_type"]] += 1
        for tag, types in sorted(tag_types.items()):
            print(f"  {tag}: {dict(types)}")

        # Save results
        out_path = RESULTS_DIR / "04_scanned_render_analysis.json"
        with open(out_path, "w") as f:
            json.dump(rendered_results, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
