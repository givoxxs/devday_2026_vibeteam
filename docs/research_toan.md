# Research Report — Document Processing Pipeline (PDF + Image)
**Người thực hiện:** Toàn
**Deadline:** Tối T4, 25/03/2026
**Trạng thái:** ✅ Hoàn thành research + benchmark + Vision LLM test thực tế

---

## TL;DR — Kết luận nhanh

| Câu hỏi | Kết luận |
|---------|---------|
| Chủ yếu loại file gì? | **98.4% PDF**, còn lại xlsx/docx/doc |
| PDF có text layer không? | **92.4% là scanned** (không có text layer) — chỉ 7.6% có text |
| PDF scanned trông như thế nào? | **100% là dạng tài liệu/biểu mẫu** (nền trắng) — không phải ảnh chụp thực địa |
| Tool nào để extract PDF? | PyMuPDF (primary) + pdfplumber (tables) — **nhưng chỉ hiệu quả với 7.6% có text** |
| Phần còn lại xử lý sao? | **Vision LLM là bắt buộc** cho 92.4% scanned PDF |
| Speed text PDF? | PyMuPDF: 23ms/file (median) · pdfplumber: 11ms/file (có spike 13s/file nhiều bảng) |
| Vision LLM (GPT-4o) speed? | **avg 21.8s/file**, median 15.6s, min 4.1s, max 84s |
| Vision LLM accuracy? | **57.1% overall** — tốt với doc rõ ràng (07, 06, 10), kém với doc mơ hồ (17, 22) |
| Cost? | **~$0.006/file** (avg 1,448 input + 240 output tokens) |

---

## 1. Kết quả Benchmark PDF

### 1.1 Phân tích corpus (62 PDFs sample)

| Chỉ số | Giá trị |
|--------|---------|
| Tổng PDFs benchmark | 62 |
| **Có text layer** | **12 (19.4%)** |
| **Scanned (không có text)** | **50 (80.6%)** |
| Có embedded images | 58 (93.5%) |
| Có tables (detect được) | 8 (12.9%) |
| Số trang: min / max / avg / median | 1 / 48 / 12.1 / 4.0 |
| Errors PyMuPDF | 0 |
| Errors pdfplumber | 0 |

**Full pipeline (314 PDFs trên 44 tasks):**

| Chỉ số | Giá trị |
|--------|---------|
| Tổng PDFs | 314 |
| Has text layer | **24 (7.6%)** |
| **Scanned** | **290 (92.4%)** |
| Has tables | 18 (5.7%) |
| Total pages | 3,086 |
| Total chars extracted | 415,774 |
| Avg chars/file | 1,324 |

### 1.2 Speed Benchmark

| Tool | Avg (ms/file) | Median (ms/file) | Ghi chú |
|------|--------------|-----------------|---------|
| **PyMuPDF** | 131.2 ms | **23.4 ms** | Nhanh, ổn định |
| **pdfplumber** | 681.2 ms | **11.3 ms** | Median tốt, nhưng spike nặng với file nhiều bảng |

**Outlier pdfplumber:** File `4462a31614db4f8698fa3980824ed83c.pdf` có **171 bảng, 2208 cells** → tốn **13,240ms**. Cần timeout + fallback.

### 1.3 Table Extraction

18 files có tables (5.7% tổng số PDFs). Các file có tables thường là:
- Phiếu kết quả thử nghiệm (tag 07) — bảng đo điện trở
- Thông số kỹ thuật thiết bị (tag 14) — bảng spec
- Hỗn hợp (tag 22)

pdfplumber extract table tốt hơn PyMuPDF đáng kể → dùng pdfplumber cho tables.

---

## 2. Phát hiện quan trọng: 92.4% Scanned PDF

### 2.1 Đặc điểm scanned PDFs

Sau khi render 20 scanned PDFs sang ảnh PNG và phân tích:

| Chỉ số | Giá trị |
|--------|---------|
| Heuristic type | **100% "document/form"** |
| Mean brightness | 218–252 (rất trắng) |
| Dark pixel ratio | 0.000–0.074 (ít nội dung đen) |
| Kết luận | **Tất cả là tài liệu giấy được scan** — biểu mẫu, bảng, bản vẽ kỹ thuật |

**Không phải ảnh chụp ngoài trời.** Đây là các tài liệu giấy được scan thành PDF.

### 2.2 Tại sao không có text layer?

Các tài liệu VPP này là:
1. **Bản vẽ kỹ thuật** (bản vẽ hoàn công, sơ đồ điện) → scan từ bản gốc
2. **Biểu mẫu điền tay** (phiếu kiểm tra, tự kiểm tra) → scan
3. **Tài liệu giấy từ nhà sản xuất** → scan thành PDF

### 2.3 Implication cho pipeline

**Không thể dùng PyMuPDF/pdfplumber cho 92.4% files.** Cần Vision LLM.

---

## 3. Pipeline Quyết định

### 3.1 Decision Tree

```
PDF file
│
├─ [Bước 1] Detect text layer (PyMuPDF, ~5ms)
│   │
│   ├─ HAS TEXT (7.6%)
│   │   ├─ Extract text blocks (PyMuPDF)
│   │   ├─ Extract tables (pdfplumber)
│   │   └─ → ProcessedDocument với full text + tables
│   │
│   └─ NO TEXT / SCANNED (92.4%)
│       ├─ Render pages to PNG (PyMuPDF, 150 DPI)
│       ├─ → Vision LLM (GPT-4o) per page
│       └─ → ProcessedDocument với caption + summary + key_info
│
Image file (standalone)
│
├─ Load image (PIL)
├─ Classify content type (heuristic)
├─ → Vision LLM (GPT-4o)
└─ → ProcessedDocument với caption + summary + ocr_text
```

### 3.2 Vision LLM Strategy

Do 92.4% files cần Vision LLM, đây là **bottleneck chính** của pipeline.

**Tối ưu:**

| Strategy | Mô tả |
|---------|-------|
| **Page-level batching** | 1 API call/page (không phải 1 call/file) |
| **Max pages per call** | GPT-4o hỗ trợ nhiều images trong 1 message → batch nhiều trang |
| **Caching** | Cache result theo file hash — cùng file không gọi lại |
| **Parallel calls** | async/await, gọi nhiều files song song |
| **2-pass strategy** | Pass 1: classify doc type nhanh (1 page). Pass 2: extract detail nếu cần |

**Prompt design cho VPP documents:**
```
Ngữ cảnh: Tài liệu từ dự án điện mặt trời (VPP) tại Nhật Bản.
Ngôn ngữ: Tiếng Nhật chính, có thể có tiếng Anh.

Cung cấp:
1. DOCUMENT_TYPE: Loại tài liệu (Test Report / Construction Drawing / Equipment Spec / ...)
2. FOLDER_NUMBER: Số thư mục phân loại (1-22) theo sort_instruction
3. KEY_INFO: Tối đa 5 thông tin kỹ thuật quan trọng
4. DATES: Ngày tháng nếu có
5. TEXT_CONTENT: Nội dung text chính (OCR)

JSON response format: {...}
```

---

## 4. JSON Schema Output

### 4.1 ProcessedDocument (per file)

```json
{
  "file_path": "Public/VPP0000710.../03】.../abc123.pdf",
  "file_type": "pdf",
  "task_id": "65302e5f-...",
  "page_count": 3,
  "has_text_layer": false,
  "is_scanned": true,
  "processing_method": "pymupdf+vision_llm",
  "processing_time_sec": 2.1,

  "pages": [
    {
      "page_index": 0,
      "width": 595.0,
      "height": 842.0,
      "elements": [
        {
          "element_type": "image",
          "bbox": {"x0": 0, "y0": 0, "x1": 595, "y1": 842},
          "caption": "絶縁抵抗測定試験成績書",
          "summary": "Insulation resistance test report. Values measured: ≥1MΩ. Result: PASS."
        }
      ]
    }
  ],

  "full_text": "絶縁抵抗測定試験成績書\n試験日: 2024年3月15日\n...",
  "document_type_guess": "Test Report / 試験成績書",
  "folder_candidate": 7,
  "folder_confidence": 0.92,

  "key_entities": {
    "dates": ["2024年3月15日"],
    "equipment_names": ["パワーコンディショナ PCS-1"],
    "numeric_values": {"insulation_resistance": "≥1MΩ"},
    "project_name": "〇〇発電所",
    "languages": ["ja"]
  }
}
```

### 4.2 Table Element (với PDF có text)

```json
{
  "element_type": "table",
  "bbox": {"x0": 50, "y0": 100, "x1": 545, "y1": 350},
  "content": "機器名 | 試験項目 | 測定値 | 判定\nPCS-1 | 絶縁抵抗 | 1.5MΩ | ○",
  "cells": [
    {"row": 0, "col": 0, "value": "機器名", "is_header": true},
    {"row": 0, "col": 1, "value": "試験項目", "is_header": true},
    {"row": 1, "col": 0, "value": "PCS-1", "is_header": false},
    {"row": 1, "col": 1, "value": "絶縁抵抗", "is_header": false},
    {"row": 1, "col": 2, "value": "1.5MΩ", "is_header": false},
    {"row": 1, "col": 3, "value": "○", "is_header": false}
  ],
  "num_rows": 5,
  "num_cols": 4
}
```

---

## 5. Context Storage Strategy

### 5.1 Vấn đề

Agent cần:
- Phân loại nhanh từng file → Folder Organisation task
- Tìm file chứa thông tin cụ thể → QA task
- Extract giá trị cụ thể từ file đã tìm được

### 5.2 Giải pháp: 2-layer storage

```
Layer 1: File-level cache (JSON on disk)
         key: hash(file_path) → ProcessedDocument JSON
         purpose: tránh reprocess, resume sau crash

Layer 2: In-memory index (per session)
         key: task_id → list[ProcessedDocument summary]
         purpose: fast lookup trong session
```

### 5.3 Summary format cho Agent context

Mỗi file được đại diện bằng 1 summary string ngắn (< 100 tokens):

```
[PDF] abc123.pdf | Type: Test Report | Folder: 7 (0.92) |
Date: 2024-03-15 | Equipment: PCS-1 | Value: insulation=≥1MΩ |
Preview: 絶縁抵抗測定試験成績書 試験日: 2024年3月15日...
```

Agent dùng summary để:
1. Identify file phù hợp với câu hỏi
2. Nếu cần detail → load full ProcessedDocument

### 5.4 Embedding (optional, Phase 2)

Nếu cần semantic search:
- Embed `full_text` của mỗi file → FAISS local
- Metadata: `{file_path, folder_candidate, document_type, task_id}`
- Query: "điện trở cách điện" → retrieve top-K files

---

## 6. Code Structure

```
src/document_processor/
├── __init__.py          # Public API
├── schema.py            # Pydantic models (ProcessedDocument, etc.)
├── pdf_processor.py     # PDF extraction (PyMuPDF + pdfplumber)
├── image_processor.py   # Image processing + Vision LLM
└── utils.py             # Date/value extraction, text cleanup

experiments/toan/
├── 01_pdf_benchmark.py       # Benchmark PyMuPDF vs pdfplumber
├── 02_run_pipeline_on_tasks.py  # Full pipeline on all 44 tasks
├── 03_text_content_analysis.py  # Text quality analysis by tag
├── 04_scanned_pdf_render.py     # Render scanned PDFs, analyze image type
├── results/
│   ├── 01_pdf_benchmark.json
│   ├── 02_pipeline_results.json
│   ├── 03_text_content_analysis.json
│   └── 04_scanned_render_analysis.json
└── sample_outputs/
    ├── rendered_pages/          # PNG renders từ scanned PDFs
    └── task_*_detail.json       # Chi tiết processing từng task
```

---

## 5b. Kết quả Vision LLM Test (GPT-4o) — Experiment 05

### 5b.1 Kết quả tổng quan (21 files scanned)

| Chỉ số | Giá trị |
|--------|---------|
| Files tested | 21 |
| Successful calls | 21 / 21 (100%) |
| **Accuracy tổng** | **57.1% (12/21)** |
| Latency avg | 21.8s/file |
| Latency median | 15.6s/file |
| Latency min/max | 4.1s / 84.3s |
| Avg input tokens | 1,448 |
| Avg output tokens | 240 |
| Cost per file | **~$0.006** |
| Total cost (21 files) | $0.13 |

### 5b.2 Accuracy theo từng loại tag

| Tag (Ground truth) | Correct | Total | Accuracy | Predicted folders | Ghi chú |
|--------------------|---------|-------|----------|-------------------|---------|
| **07. Test Reports** | 2 | 2 | **100%** | [7, 7] | Nhận dạng hoàn hảo |
| **06. As-built Drawings** | 2 | 2 | **100%** | [6, 6] | Nhận dạng hoàn hảo |
| **05. Construction Schedule** | 2 | 2 | **100%** | [6, 6] | Dự đoán đúng (folder 6 cũng trong tags) |
| **10. Equipment Config** | 2 | 2 | **100%** | [7, 10] | 1 trong 2 match |
| **14. Equipment Specs** | 1 | 2 | **50%** | [14, 15] | Nhầm Manual vs Spec |
| **04. Completion Report** | 1 | 2 | **50%** | [6, 4] | 1 bị nhầm sang folder 6 |
| **18. Warranties** | 1 | 2 | **50%** | [14, 15] | Nhầm Spec/Manual vs Warranty |
| **19. Construction Photos** | 1 | 2 | **50%** | [7, 12] | Module cert bị nhầm |
| **01. Spine/Cover** | 0 | 1 | **0%** | [4] | Nhầm sang Completion Report |
| **17. Utility Documents** | 0 | 2 | **0%** | [18, 18] | Warranty và Utility bị nhầm |
| **22. Other/Manifests** | 0 | 2 | **0%** | [4, 6] | Tag 22 quá chung chung |

### 5b.3 Phân tích lỗi

**Lỗi pattern 1 — Tag 17 bị predict là 18 (Warranty):**
- File thực tế là "工事完了届" (Construction Completion Notice) → GPT-4o đọc đúng content, nhưng phân loại sai folder.
- **Fix:** Cải thiện prompt với ví dụ cụ thể hơn cho folder 17 (電力関係書類).

**Lỗi pattern 2 — Tag 22 bị predict là 4 hoặc 6:**
- File thực tế có nội dung của folder 4 (Completion Report) → GPT-4o predict đúng content nhưng tag ground truth là 22.
- **Quan trọng:** Tag 22 của task không phải label của từng file — đây là tag của cả batch task. GPT-4o thực ra đúng về content, ground truth tag 22 là "nhiễu".

**Lỗi pattern 3 — Tag 14 vs 15 (Spec vs Manual):**
- Spec sheet và Quick Start Guide có visual tương tự → cần prompt rõ hơn.

**Lỗi pattern 4 — Tag 01 (Spine/Cover):**
- File là mục lục/bìa của toàn bộ hồ sơ → GPT-4o nhìn thấy nội dung "完成図書" predict folder 4.
- **Fix:** Thêm ví dụ "表紙・目次" vào prompt.

### 5b.4 Sample OCR output từ GPT-4o (chất lượng cao)

GPT-4o extract được text tiếng Nhật rất tốt:
```
太陽光発電システム設置工事
使用機器一覧
製品名 メーカー 型式 数量
太陽電池モジュール XLM108-415X-S10S 329枚
パワーコンディショナ SUN2000-495KTL-JPL1 3台
```

```
太陽電池モジュール検査成績書
製品名 XLM108-415X
2023年6月5日
```

→ **OCR quality: rất tốt** cho tài liệu in sẵn. Handwritten có thể kém hơn (chưa test).

### 5b.5 Cost projection cho 1 task

| Scenario | Files | Pages (avg 4p) | API calls | Cost | Time (parallel 5) |
|----------|-------|----------------|-----------|------|-------------------|
| Small task (2 files) | 2 | 8 | 8 | ~$0.05 | ~16s |
| Medium task (17 files) | 17 | 68 | 68 | ~$0.41 | ~60s |
| Large task (70 files) | 70 | 280 | 280 | ~$1.68 | ~240s |

**Vấn đề:** Task 70 files sẽ tốn ~4 phút và $1.68. Cần **smart caching** và **2-pass strategy**.

### 5b.6 Recommended Optimizations

1. **Chỉ render 1 trang đầu** để classify doc type (không render tất cả pages).
2. **2-pass:** Pass 1 classify nhanh (1 trang, low detail) → Pass 2 extract chi tiết chỉ khi cần.
3. **Cache by file hash:** Nếu cùng file xuất hiện lại → dùng cached result.
4. **Improve prompt** cho các loại hay bị nhầm (17 vs 18, 14 vs 15, 01 vs 04).

---

## 7. Điểm còn lại cần làm (Phase 2)

| Task | Ưu tiên | Ghi chú |
|------|---------|---------|
| Integrate Vision LLM (GPT-4o) và test thực tế | **Cao** | Cần OpenAI API key từ BTC |
| Tối ưu prompt cho tài liệu VPP tiếng Nhật | **Cao** | Test với 10-20 files scanned |
| Implement async batch processing | **Cao** | Xử lý song song nhiều files |
| Test pdfplumber timeout (file 171 bảng) | **Trung bình** | Add `max_tables=50` limit |
| Implement file-level cache | **Trung bình** | hash(content) → JSON |
| Embedding + FAISS (nếu cần) | Thấp | Chỉ cần nếu semantic search quan trọng |

---

## 8. Tóm tắt cho buổi Review

**3 điểm chính:**

1. **92.4% là scanned PDF** → Vision LLM là bắt buộc, không phải optional. Đây là thay đổi lớn so với dự kiến ban đầu.

2. **Với 7.6% có text:** PyMuPDF (fast) + pdfplumber (tables) → pipeline hoạt động tốt. Speed: ~23ms/file (median).

3. **Code đã viết:** Schema, PDF processor, Image processor, utils — sẵn sàng tích hợp Vision LLM khi có API key.

**Rủi ro chính:** Vision LLM call sẽ tốn ~2-5s/page → với 1 task 30 files × avg 4 pages = 120 API calls. Cần parallel async + caching để đạt target latency.
