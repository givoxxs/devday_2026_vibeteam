# Task của Toàn — Survey Process Data: PDF + IMAGE

> **Deadline:** Tối T4, 25/03/2026
> **Mục tiêu:** Xác định đầy đủ pipeline, tools, format và cách lưu context cho việc xử lý file PDF và Image — phục vụ làm input cho Agent.

---

## Bức tranh tổng thể — Toàn làm gì?

Trong pipeline của Agent, **Bước 2 (Process Documents)** là nền tảng quan trọng nhất:
- Nếu extract sai/thiếu → Agent trả lời sai dù logic đúng.
- Nếu extract chậm → điểm Efficiency giảm.
- Nếu không có `bbox`/`position` → Validator không validate được.

**Toàn chịu trách nhiệm phần PDF + IMAGE** — 2 loại file phức tạp nhất (scan, multi-column, bảng nhúng trong ảnh, v.v.).

---

## 4 câu hỏi cần trả lời

### 1. Pipeline & Tools cần có là gì?

Xác định chuỗi xử lý cho từng loại file:

**PDF:**
```
PDF file
  ├── [Có text layer?]
  │     YES → Docling / PyMuPDF extract text + tables + images
  │     NO  → Detect as scanned → Vision LLM / OCR pipeline
  └── Output: JSON chuẩn hoá
```

**Image (PNG, JPG, TIFF, v.v.):**
```
Image file
  ├── Detect content type (photo / diagram / table / drawing)
  ├── OCR nếu có text trong ảnh
  ├── Vision LLM → caption + summary
  └── Output: JSON chuẩn hoá
```

**Cần làm:**
- [ ] Test Docling trên vài file PDF mẫu — xem chất lượng extract text, table, image.
- [ ] Test PyMuPDF — so sánh tốc độ và chất lượng với Docling.
- [ ] Xác định: PDF nào là scan (cần OCR) vs. PDF có text layer.
- [ ] Chọn Vision LLM cho ảnh: GPT-4o vision / Claude vision / Gemini vision.
- [ ] Xác định khi nào cần OCR thêm (Tesseract / EasyOCR / Surya).

---

### 2. Phương pháp process & thư viện cho từng loại?

#### PDF — Đề xuất so sánh

| Thư viện | Ưu điểm | Nhược điểm | Khi nào dùng |
|----------|---------|-----------|--------------|
| **Docling** | Extract cấu trúc tốt, hiểu table/layout, output JSON | Chậm hơn | PDF phức tạp, multi-column, nhiều bảng |
| **PyMuPDF (fitz)** | Nhanh, lấy được bbox chính xác | Ít hiểu layout | PDF đơn giản, cần tốc độ |
| **Vision LLM** | Hiểu cả scan, diagram, handwriting | Tốn token, chậm | PDF scan, không có text layer |
| **pdfplumber** | Extract table tốt | Không handle image | Khi cần extract bảng chính xác |

**Cần làm:**
- [ ] Benchmark 3 thư viện trên tập file mẫu (tốc độ + chất lượng).
- [ ] Quyết định: dùng Docling làm primary, PyMuPDF làm fallback?
- [ ] Xử lý trường hợp mixed PDF (vừa có text layer vừa có ảnh scan).

#### Image — Đề xuất pipeline

```python
# Bước 1: Detect loại ảnh
content_type = classify_image(image)
# → "photo", "technical_drawing", "table", "handwritten", "mixed"

# Bước 2: OCR nếu có text
if content_type in ["table", "technical_drawing", "handwritten"]:
    ocr_text = ocr_engine(image)  # EasyOCR hoặc Surya

# Bước 3: Vision LLM
caption, summary = vision_llm(image, prompt=...)

# Bước 4: Structured output
result = {
    "type": "image",
    "content_type": content_type,
    "ocr_text": ocr_text,
    "caption": caption,
    "summary": summary,
    "bbox": None  # ảnh là file riêng, không có bbox
}
```

**Cần làm:**
- [ ] Xác định Vision LLM: GPT-4o / Claude Sonnet (cái nào tốt hơn cho ảnh kỹ thuật điện mặt trời).
- [ ] Thiết kế prompt cho Vision LLM: extract thông tin kỹ thuật từ ảnh thi công, bản vẽ, bảng.
- [ ] Test EasyOCR vs Surya vs Tesseract cho ảnh có text Nhật/tiếng Anh.

---

### 3. Định dạng output — Lưu field gì, data gì?

#### Schema cho PDF element

```python
# Mỗi element trong một page của PDF
{
    "element_id": "site01_report_p2_elem3",   # unique id
    "file_path": "site_01/electrical/report.pdf",
    "file_type": "pdf",
    "page_index": 2,
    "element_type": "text" | "table" | "image",

    # Với text:
    "content": "...",
    "bbox": [x0, y0, x1, y1],   # toạ độ trên trang (pixel hoặc pt)

    # Với table:
    "content": "...",           # raw text của bảng
    "bbox": [x0, y0, x1, y1],
    "table_data": [
        {"row": 0, "col": 0, "value": "Hạng mục", "is_header": true},
        {"row": 1, "col": 0, "value": "Điện trở cách điện", "is_header": false},
        {"row": 1, "col": 1, "value": "≥ 1MΩ", "is_header": false},
    ],

    # Với image (nhúng trong PDF):
    "image_bytes": "<base64>",   # hoặc lưu file
    "caption": "...",
    "summary": "...",
    "bbox": [x0, y0, x1, y1],
}
```

#### Schema cho Image file (file ảnh độc lập)

```python
{
    "element_id": "site01_photo_001",
    "file_path": "site_01/photos/panel_installation.jpg",
    "file_type": "image",
    "content_type": "photo" | "technical_drawing" | "table" | "diagram",
    "ocr_text": "...",           # text nhận dạng được trong ảnh
    "caption": "...",            # mô tả ngắn nội dung ảnh
    "summary": "...",            # tóm tắt thông tin kỹ thuật trong ảnh
    "detected_keywords": ["solar panel", "PCS", "grid connection"],
    "metadata": {
        "width": 1920,
        "height": 1080,
        "format": "JPEG"
    }
}
```

#### File-level summary (quan trọng cho Folder Organisation)

```python
{
    "file_path": "...",
    "file_type": "pdf" | "image",
    "document_type_guess": "Test Report",   # dự đoán loại tài liệu
    "folder_candidate": 7,                   # số thư mục candidate
    "folder_confidence": 0.85,
    "key_entities": {
        "dates": ["2024-03-15"],
        "equipment": ["PCS-100kW", "Module A-series"],
        "values": {"insulation_resistance": "≥ 1MΩ"},
        "project_name": "...",
        "site_id": "site_01"
    },
    "language": "ja" | "en" | "vi",
    "page_count": 3,                         # cho PDF
    "elements": [...]                         # list các element trên
}
```

**Cần làm:**
- [ ] Finalize schema với cả đội (đặc biệt với Mạnh — Excel/Doc).
- [ ] Quyết định lưu image bytes hay lưu file path.
- [ ] Quyết định format lưu: JSON files hay SQLite hay in-memory dict?

---

### 4. Lưu Context như thế nào để nạp cho Agent?

#### Chiến lược context

Agent cần context để:
1. **Trả lời Q&A:** Tìm đoạn văn bản liên quan → trả lời.
2. **Folder Organisation:** Đọc summary của file → phân loại.
3. **Validation:** Lấy lại evidence để kiểm tra.

#### Phương án đề xuất: Hybrid (Vector Search + Direct Lookup)

```
Processed Files
      │
      ├── [Full JSON] ──→ Lưu vào disk (cache)
      │                   Key: file_path
      │
      └── [Embeddings] → Lưu vào Vector Store (FAISS local)
                         Mỗi element → 1 vector
                         Metadata: {file_path, page, element_type, bbox}
```

**Khi Agent cần context:**
- **Search semantic:** Query → vector search → top-K elements → truyền vào LLM.
- **Direct lookup:** Biết file cụ thể → load JSON → lấy element theo id.
- **Table lookup:** Filter by `element_type=table` → dùng cho câu hỏi về số liệu.

**Cần làm:**
- [ ] Quyết định vector store: FAISS (offline, nhanh) hay ChromaDB (dễ query hơn).
- [ ] Quyết định embedding model: `text-embedding-3-small` (nhanh, rẻ) hay `text-embedding-3-large` (chính xác hơn).
- [ ] Thiết kế chunking strategy: chunk theo element (1 element = 1 vector) hay chunk theo paragraph?
- [ ] Thiết kế metadata để filter hiệu quả (filter by `file_path`, `element_type`, `page_index`).
- [ ] Viết interface `DocumentStore` với các method: `add_file()`, `search()`, `get_by_id()`, `get_summary()`.

---

## Deliverables của Toàn (Deadline: Tối T4, 25/03)

### Phải có (Must have)

- [ ] **Report so sánh tools:** Docling vs PyMuPDF vs Vision LLM cho PDF — kết luận rõ "dùng cái gì cho case nào".
- [ ] **Report tools cho Image:** Vision LLM nào tốt nhất cho ảnh kỹ thuật — kết luận rõ.
- [ ] **Schema JSON chuẩn hoá:** Định nghĩa đầy đủ output format cho PDF element và Image element.
- [ ] **Context strategy:** Quyết định rõ cách lưu và nạp context cho Agent (vector store + metadata design).

### Nên có (Should have)

- [ ] **Code mẫu:** Function `process_pdf(file_bytes) → List[Element]`.
- [ ] **Code mẫu:** Function `process_image(file_bytes) → ImageElement`.
- [ ] **Test** trên ít nhất 3-5 file mẫu từ public data.

### Output format của buổi review (T4 tối)

Trình bày dưới dạng markdown / slides:
1. Tools đã test + kết quả benchmark (tốc độ, chất lượng).
2. Pipeline cuối cùng cho PDF và Image.
3. Schema JSON finalized.
4. Context storage strategy.
5. Các vấn đề/câu hỏi cần thống nhất với cả đội.

---

## Lưu ý quan trọng

> **Tại sao `bbox` quan trọng?**
> Validator cần biết thông tin được lấy từ đâu trong tài liệu để kiểm tra lại tránh hallucination. Nếu Agent nói "điện trở cách điện = 1.5 MΩ" nhưng không có bbox, Validator không thể xác nhận. **Mọi element extract ra phải có position.**

> **Tại sao file-level summary quan trọng?**
> Với Folder Organisation task, Agent cần phân loại file vào 1 trong 21 thư mục. Nếu phải đọc toàn bộ file mỗi lần → chậm, tốn token. Có sẵn `document_type_guess` + `key_entities` → phân loại nhanh hơn nhiều.

> **Với ảnh kỹ thuật (bản vẽ, sơ đồ điện):**
> Vision LLM phải được prompt kỹ để extract thông tin kỹ thuật (tên thiết bị, thông số, mã số), không chỉ mô tả chung chung.
