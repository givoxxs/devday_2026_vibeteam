# Hướng làm — VPP AI Agent

> Kiến trúc tổng thể và hướng tiếp cận của đội

---

## Kiến trúc tổng thể

```
┌─────────────────────────────────────────────────────────────┐
│                        AI AGENT                             │
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────┐  │
│  │   Planner    │──▶│   Executor   │──▶│   Validator    │  │
│  │              │   │              │   │                │  │
│  │ - Parse task │   │ - Call tools │   │ - Input valid? │  │
│  │ - Sub-tasks  │   │ - Process    │   │ - Plan valid?  │  │
│  │ - Seq/Para?  │   │   docs       │   │ - Output ok?   │  │
│  └──────────────┘   └──────────────┘   └────────────────┘  │
│          │                  │                   │           │
│          └──────────────────┴───────────────────┘          │
│                         Context/State                       │
│                    (Plan + Results + Deps)                  │
└─────────────────────────────────────────────────────────────┘
         │                                        │
         ▼                                        ▼
   Simulator API                          Document Store
   (tasks/next,                           (processed files
    submissions)                           + embeddings)
```

---

## Pipeline xử lý một Task

```
GET /tasks/next
     │
     ▼
[Bước 1] Parse Prompt Template
     ├── Xác định số lượng sub-question
     ├── Xác định loại thông tin cần tìm (text / table / image)
     ├── Xác định dependency giữa các sub-question
     └── Quyết định: tuần tự hay song song

     │
     ▼
[Bước 2] Process Documents (song song)
     ├── PDF     → Docling / LLM → JSON có bbox
     ├── Image   → Vision model → caption + summary + OCR
     ├── Excel   → pandas → dataframe → JSON
     └── Doc     → text extraction → JSON

     │
     ▼
[Bước 3] Lên Plan & Execute
     ├── Với Q&A task: search → extract → answer
     └── Với Folder task: classify → assign folder

     │
     ▼
[Bước 4] Validate
     ├── Kiểm tra input có hợp lệ không
     ├── Kiểm tra plan có đúng không
     └── Kiểm tra output có đúng không

     │
     ▼
POST /submissions
     (answers + thought_log + used_tools)
```

---

## Bước 1: Xử lý Prompt Template

**Mục tiêu:** Chia nhỏ yêu cầu lớn → các vấn đề nhỏ có thể thực thi.

**Logic:**
- Đọc `prompt_template` → parse bằng LLM → trả về danh sách sub-tasks có structured output.
- Với mỗi sub-task: xác định `type` (`qa`, `classify`), `requires` (dependency), `info_type` (`text`/`table`/`image`).
- Ví dụ parse:
  ```
  "Xác định phiếu kết quả thử nghiệm và kiểm tra giá trị điện trở cách điện"
  → sub-task 1: identify document type = "Test Report/Inspection Sheet" [type: classify]
  → sub-task 2: extract value of "điện trở cách điện" from identified doc [type: qa, requires: sub-task 1]
  ```

---

## Bước 2: Xử lý Documents

**Nguyên tắc:**
- Xử lý **song song** các file để tiết kiệm thời gian.
- Store kết quả sau khi trích xuất (tránh xử lý lại).
- Mỗi element trích xuất phải có `bbox`/`position` để validation.

**Tool stack:**
| Loại file | Tool chính | Fallback |
|-----------|-----------|---------|
| PDF (có text) | Docling | PyMuPDF |
| PDF (scan/ảnh) | Vision LLM + OCR | Tesseract |
| Image | Vision LLM (GPT-4o / Claude) | OCR |
| Excel | pandas | openpyxl |
| Doc | python-docx | Docling |

**Output chuẩn hoá:** JSON theo schema đã định nghĩa (xem [problem_understanding.md](problem_understanding.md)).

---

## Bước 3: Lên Plan & Execute

### Với Q&A task:
```
[Plan] → search in processed docs → extract relevant content → format answer
```
- Sử dụng **vector search** (text_embedding_3) để tìm đoạn liên quan.
- Với câu hỏi về bảng: search theo `type=table`, extract giá trị cụ thể.
- Với câu hỏi về ảnh: dùng caption/summary đã sinh từ Bước 2.

### Với Folder Organisation task:
```
[Plan] → read doc summary → match với 21 folder rules → assign folder number
```
- Build **RAG** với nội dung 21 folder rules (từ sort_instruction).
- Dùng embedding similarity + LLM reasoning để phân loại.
- Ghi lý luận chi tiết vào `thought_log`.

---

## Bước 4: Validate

**3 tầng validation:**

| Tầng | Kiểm tra | Hành động nếu fail |
|------|----------|--------------------|
| Input | Extracted content hợp lệ, đủ dữ liệu | Re-extract với strategy khác |
| Plan | Sub-tasks đúng logic, đủ dependencies | Re-plan |
| Output | Câu trả lời hợp lý, có evidence | Re-execute sub-task liên quan |

**Quan trọng:** Validator tạo checklist riêng cho từng task, không hardcode.

---

## Chiến lược tối ưu Score

### Accuracy (Precision & Meaning match)
- Extract có `bbox` → validate không bịa.
- Với số liệu: trích xuất nguyên văn, không tự tính lại.
- Với phân loại: so khớp định nghĩa trong sort_instruction.

### Efficiency (Latency & Tokens)
- Xử lý file song song.
- Cache kết quả process file (tránh re-process nếu resume session).
- Dùng embedding search thay vì đọc toàn bộ file cho mỗi câu hỏi.
- Chỉ truyền context liên quan vào LLM (không dump toàn bộ file).

### Robustness (Error handling)
- Retry với exponential backoff cho API calls.
- Fallback tool khi primary tool fail.
- Refresh Bearer token tự động khi 401.
- Resume session khi process bị gián đoạn.

### Qualitative (Planning, Self-correction, Memory, Safety)
- `thought_log` chi tiết, có reasoning rõ ràng.
- Log `used_tools` đầy đủ.
- Self-correction: nếu Validator fail → update plan → retry.
- RAG memory: lưu kết quả xử lý các file đã gặp để tái sử dụng.

---

## Tech Stack đề xuất

| Component | Tech |
|-----------|------|
| Agent framework | Custom Python (httpx + asyncio) |
| LLM | GPT-4o (provided API key) |
| Document processing | Docling + PyMuPDF + Vision LLM |
| Embedding | text-embedding-3-small/large |
| Vector store | FAISS / ChromaDB (local) |
| Async processing | asyncio / concurrent.futures |
| Data format | JSON (structured output) |
