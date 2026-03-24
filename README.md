# VPP AI Agent Challenge — DevDay 2026

Repo của team thi **VPP AI Agent Challenge** — xây dựng AI Agent quản lý hồ sơ hoàn công công trình điện mặt trời (VPP), tổ chức tại DevDay 2026.

> **Deadline nộp bài:** 12/04/2026 · **Thuyết trình:** 18/04/2026

---

## Tổng quan bài toán

Hệ thống AI Agent phân loại và xử lý tài liệu hồ sơ hoàn công dự án điện mặt trời tại Nhật Bản. Tài liệu chủ yếu là PDF scan tiếng Nhật, cần phân loại vào 21 thư mục theo chuẩn VPP.

**3 Phase thi đấu:**

| Phase | Mô tả |
|-------|-------|
| 1 — Observability | Agent quan sát, hiểu được cấu trúc tài liệu |
| 2 — Action Generation | Agent sinh action: trả lời câu hỏi + phân loại thư mục |
| 3 — Verifiability | Agent tự kiểm tra và sửa lỗi |

**2 loại task per phase:**
- **Question Answering (QA):** Trả lời câu hỏi về nội dung tài liệu
- **Folder Organisation:** Phân loại tài liệu vào đúng thư mục (1–21)

---

## Cấu trúc Repo

```
DevDay2026/
├── README.md
├── .env                          # OPENAI_KEY (không commit)
│
├── src/
│   └── document_processor/       # Package xử lý tài liệu (production)
│       ├── schema.py             # Pydantic models: ProcessedDocument, PageContent, ...
│       ├── pdf_processor.py      # PDF: PyMuPDF + pdfplumber
│       ├── image_processor.py    # Image/scanned PDF: GPT-4o vision
│       └── utils.py              # Helpers: extract_dates, detect_language, ...
│
├── experiments/
│   └── toan/                     # Thực nghiệm document processing
│       ├── 01_pdf_benchmark.py   # Benchmark PyMuPDF vs pdfplumber
│       ├── 02_run_pipeline_on_tasks.py  # Pipeline trên 44 tasks
│       ├── 03_text_content_analysis.py # Phân tích text quality
│       ├── 04_scanned_pdf_render.py    # Render scanned PDF → PNG
│       ├── 05_vision_llm_test.py       # GPT-4o vision test + accuracy
│       └── results/              # JSON output của mỗi experiment
│
├── data/                         # Public data — 44 tasks (không commit)
│   └── task_XXXX-XXXX/
│       ├── task_info_vi.json     # Ground truth: tags_vi, resources_info
│       └── Public/
│           └── VPP0000XXX_masked/
│
├── docs/                         # Tài liệu nghiên cứu và tổng hợp
│   ├── competition_overview.md   # Luật thi, cách chấm điểm, lịch trình
│   ├── api_reference.md          # Simulator API reference
│   ├── folder_structure_rules.md # 21 thư mục phân loại (EN/JP/VN)
│   ├── problem_understanding.md  # Hiểu bài toán, 2 loại task
│   ├── approach.md               # Kiến trúc tổng thể, hướng làm
│   ├── task_toan.md              # Task chi tiết của Toàn
│   ├── data_analysis.md          # Phân tích 44 tasks, 744 files
│   ├── data_patterns.md          # Pattern QA, keyword mapping
│   ├── research_toan.md          # Research report: benchmark + Vision LLM
│   └── code_structure_toan.md    # Mô tả cấu trúc code + output
│
├── idea/                         # Note ý tưởng ban đầu của team
└── Metadata/                     # PDF tài liệu đề bài gốc
```

---

## Phát hiện kỹ thuật quan trọng

| Phát hiện | Giá trị |
|-----------|---------|
| **92.4% PDF là scanned** (không có text layer) | → Vision LLM là bắt buộc |
| 100% scanned PDF là dạng tài liệu giấy (nền trắng) | → Không phải ảnh chụp thực địa |
| PyMuPDF speed | 23ms/file (median) |
| pdfplumber có outlier | 13,240ms với file 171 bảng → cần timeout |
| GPT-4o accuracy (zero-shot) | **57.1%** (21 files, 11 tags) |
| GPT-4o latency | avg 21.8s, median 15.6s/file |
| GPT-4o cost | ~$0.006/file |

---

## Setup

```bash
# 1. Tạo file .env
echo "OPENAI_KEY=sk-proj-..." > .env

# 2. Cài dependencies
conda run -n devday pip install pymupdf pdfplumber pillow openai pydantic python-dotenv

# 3. Chạy thực nghiệm
conda run -n devday python experiments/toan/01_pdf_benchmark.py
conda run -n devday python experiments/toan/05_vision_llm_test.py
```

**Yêu cầu:** Python 3.12, conda env `devday`, thư mục `data/` với 44 tasks.

---

## Pipeline Xử lý Tài liệu

```
PDF file
│
├─ Detect text layer (~5ms)
│   │
│   ├─ HAS TEXT (7.6%)  → PyMuPDF text + pdfplumber tables → ProcessedDocument
│   │
│   └─ SCANNED (92.4%) → Render PNG → GPT-4o Vision → ProcessedDocument
│
ProcessedDocument
├── folder_candidate: 7          # Folder dự đoán
├── folder_confidence: 0.92      # Độ tin cậy
├── full_text: "絶縁抵抗..."      # Text (OCR hoặc extract)
└── key_entities: { dates, equipment, numeric_values }
```

Chi tiết: [docs/code_structure_toan.md](docs/code_structure_toan.md) · [docs/research_toan.md](docs/research_toan.md)

---

## Tài liệu tham khảo

| File | Nội dung |
|------|---------|
| [docs/competition_overview.md](docs/competition_overview.md) | Luật thi, 3 phase, cách chấm điểm |
| [docs/api_reference.md](docs/api_reference.md) | Simulator API: /sessions, /tasks/next, /submissions |
| [docs/folder_structure_rules.md](docs/folder_structure_rules.md) | 21 thư mục phân loại (EN/JP/VN) |
| [docs/approach.md](docs/approach.md) | Kiến trúc agent, hướng tiếp cận |
| [docs/data_analysis.md](docs/data_analysis.md) | Phân tích 44 tasks public data |
| [docs/research_toan.md](docs/research_toan.md) | Benchmark + Vision LLM research report |

---

## Team

| Thành viên | Task |
|-----------|------|
| **Toàn** | Document processing pipeline, PDF/Image extraction, Vision LLM research |
| **Lý** | Agent architecture, Simulator API integration, orchestration |

---

## Ghi chú

- Tất cả lệnh chạy qua `conda run -n devday` (Python 3.12)
- File `data/` và `.env` không commit vào git
- Kết quả experiment lưu tại `experiments/toan/results/*.json`
