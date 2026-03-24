"""
Experiment 03: Analyze extracted text content quality.
- Show actual text extracted from representative files per tag type
- Validate extraction quality vs ground truth tags
- Identify patterns in text that help classify document types

Run: conda run -n devday python experiments/toan/03_text_content_analysis.py
"""
import json
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import fitz
import pdfplumber

DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


def load_all_tasks() -> list[dict]:
    tasks = []
    for task_dir in sorted(DATA_DIR.iterdir()):
        if not task_dir.is_dir(): continue
        vi_path = task_dir / "task_info_vi.json"
        if not vi_path.exists(): continue
        with open(vi_path) as f:
            vi = json.load(f)
        vi["task_dir"] = str(task_dir)
        tasks.append(vi)
    return tasks


def extract_text_sample(pdf_path: str, max_chars: int = 1000) -> str:
    """Extract text from first 2 pages of PDF."""
    try:
        doc = fitz.open(pdf_path)
        texts = []
        for i in range(min(2, doc.page_count)):
            texts.append(doc[i].get_text("text").strip())
        doc.close()
        return "\n".join(texts)[:max_chars]
    except Exception as e:
        return f"[ERROR: {e}]"


def get_one_file_per_tag(tasks: list[dict]) -> dict[str, list[dict]]:
    """For each unique tag, collect up to 3 file examples."""
    tag_files = defaultdict(list)
    for task in tasks:
        tags = task.get("tags_vi", [])
        resources = task.get("resources_info", [])
        task_dir = Path(task["task_dir"])
        for res in resources[:3]:  # first 3 files
            file_path = task_dir / res["file_path"]
            if file_path.exists() and res.get("file_type") == "pdf":
                for tag in tags:
                    if len(tag_files[tag]) < 3:
                        tag_files[tag].append({
                            "path": str(file_path),
                            "name": file_path.name,
                            "task_id": task.get("task_id", "")[:8],
                        })
    return dict(tag_files)


def analyze_text_by_tag(tag_files: dict) -> dict:
    """Extract text and analyze patterns per tag."""
    results = {}
    for tag, files in sorted(tag_files.items()):
        print(f"\n{'='*60}")
        print(f"TAG: {tag}")
        print(f"{'='*60}")
        tag_result = {"tag": tag, "files": []}

        for file_info in files:
            text = extract_text_sample(file_info["path"])
            if text.startswith("[ERROR"):
                continue
            print(f"\n  File: {file_info['name']} (task_{file_info['task_id']})")
            print(f"  Length: {len(text)} chars")
            print(f"  Preview:\n    {text[:400].replace(chr(10), chr(10)+'    ')}")

            tag_result["files"].append({
                "name": file_info["name"],
                "task_id": file_info["task_id"],
                "text_length": len(text),
                "text_preview": text[:400],
                "has_japanese": any('\u3040' <= c <= '\u30FF' or '\u4E00' <= c <= '\u9FFF' for c in text),
                "has_numbers": any(c.isdigit() for c in text),
            })

        results[tag] = tag_result
    return results


def detect_keywords_by_tag(tag_files: dict) -> dict:
    """Find distinctive keywords in each tag's documents."""
    TAG_KEYWORDS = {
        "07. Phieu ket qua thu nghiem": ["試験", "検査", "判定", "絶縁", "接地", "合格", "不合格", "MΩ"],
        "17. Ho so thu tuc dien luc": ["電力", "系統", "連系", "契約", "申請", "費用"],
        "19. Anh thi cong": ["写真", "工事", "施工", "設置"],
        "14. Thong so ky thuat": ["仕様", "スペック", "型式", "定格", "出力", "kW"],
        "11. PCS": ["パワーコンディショナ", "PCS", "インバータ", "定格出力"],
        "02. Muc luc": ["目次", "インデックス", "一覧"],
        "18. Bao hanh": ["保証", "保障", "warranty"],
        "01. Bia": ["表紙", "物件名", "プロジェクト"],
    }

    results = {}
    for tag, files in tag_files.items():
        # Find matching keyword set
        keyword_set = None
        for kw_tag, kws in TAG_KEYWORDS.items():
            if kw_tag in tag:
                keyword_set = kws
                break

        if not keyword_set:
            continue

        hit_counts = defaultdict(int)
        for file_info in files:
            text = extract_text_sample(file_info["path"], max_chars=3000)
            for kw in keyword_set:
                if kw.lower() in text.lower():
                    hit_counts[kw] += 1

        results[tag] = {
            "keywords_tested": keyword_set,
            "hits": dict(hit_counts),
            "files_tested": len(files),
        }

    return results


def main():
    print("=== Text Content Analysis by Tag ===\n")
    tasks = load_all_tasks()
    print(f"Loaded {len(tasks)} tasks")

    tag_files = get_one_file_per_tag(tasks)
    print(f"Tags found: {sorted(tag_files.keys())}")

    # Analyze text per tag
    text_results = analyze_text_by_tag(tag_files)

    # Keyword detection
    print("\n\n" + "="*60)
    print("KEYWORD DETECTION BY TAG")
    print("="*60)
    keyword_results = detect_keywords_by_tag(tag_files)
    for tag, res in keyword_results.items():
        print(f"\n{tag}:")
        print(f"  Files tested: {res['files_tested']}")
        print(f"  Keywords found: {res['hits']}")
        print(f"  Missing: {[k for k in res['keywords_tested'] if k not in res['hits']]}")

    # Save
    out_path = RESULTS_DIR / "03_text_content_analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({
            "text_by_tag": text_results,
            "keyword_detection": keyword_results,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
