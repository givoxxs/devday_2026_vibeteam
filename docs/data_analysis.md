# Phân tích dữ liệu Public — VPP AI Agent Challenge

> Phân tích toàn bộ 44 tasks trong thư mục `data/`

---

## 1. Tổng quan số liệu

| Chỉ số | Giá trị |
|--------|---------|
| Tổng số tasks | **44** |
| Tổng số files | **744** |
| Loại file PDF | **732 (98.4%)** |
| Loại file xlsx | 8 (1.1%) |
| Loại file docx | 2 (0.3%) |
| Loại file doc | 2 (0.3%) |
| Số files trung bình / task | 16.9 |
| Min files / task | 2 |
| Max files / task | 70 |
| Số sites (dự án VPP) | **6** |

**Nhận xét quan trọng:** Gần như toàn bộ dữ liệu là **PDF**. xlsx, docx, doc chỉ xuất hiện lẻ tẻ → ưu tiên tối ưu PDF pipeline.

---

## 2. Cấu trúc dữ liệu mỗi Task

Mỗi task folder chứa:
```
task_<uuid>/
├── task_info.json       ← prompt tiếng Nhật, danh sách file
├── task_info_vi.json    ← prompt tiếng Việt + tags_vi (ground truth!)
└── Public/
    └── <site_id>/
        └── <folder_masked>/
            └── <hash>.pdf  (hoặc xlsx/docx/doc)
```

### Ground truth trong `task_info_vi.json`

```json
{
  "tags_vi": ["07. Phieu ket qua thu nghiem / Bang kiem tra"],
  "tags_jp": ["07. 試験成績書・検査表"]
}
```

> **Quan trọng:** `tags_vi` là nhãn đúng của task (folder đích). Đây là dữ liệu huấn luyện / để đánh giá độ chính xác trong dev phase.

---

## 3. Hai loại Task (50/50)

| Loại | Số lượng | Đặc điểm |
|------|----------|----------|
| **Folder Organisation** | 22 | Phân loại toàn bộ files vào thư mục, không có Q cụ thể |
| **Question Answering (QA)** | 22 | Xác định file → trích xuất thông tin cụ thể |

### Phân biệt bằng prompt

**Folder tasks** — prompt chỉ yêu cầu phân loại:
- "Dựa trên nội dung tài liệu, hãy xác định phân loại và sắp xếp vào thư mục phù hợp."
- "Xác định phân loại dựa trên nội dung tài liệu và sắp xếp vào thư mục phù hợp."
- "Hãy sắp xếp vào thư mục dựa trên nội dung tài liệu."

**QA tasks** — prompt đặt câu hỏi cụ thể:
- "Xác định X và kiểm tra Y"
- "Xác định X và xác nhận Y"
- "Hãy xác định X và [trích xuất thông tin Z]"

---

## 4. Phân bố theo Sites (6 dự án VPP)

| Site ID | Files | Tasks | File types |
|---------|-------|-------|-----------|
| `01_masked_758cbc89` | 240 | 8 | pdf(236), xlsx(2), docx(2) |
| `VPP0000628_masked_690716f0` | 122 | 6 | pdf(122) |
| `VPP0000666_masked_916e109a` | 114 | 8 | pdf(108), xlsx(4), doc(2) |
| `VPP0000710_masked_9e5bdb67` | 94 | 6 | pdf(94) |
| `VPP0000613_masked_68cfa989` | 84 | 8 | pdf(84) |
| `VPP0000935_masked_d648f74a` | 90 | 8 | pdf(88), xlsx(2) |

**Nhận xét:**
- Mỗi site có **6-8 tasks** — phân bổ tương đối đều.
- `01_masked_758cbc89` lớn nhất (240 files, 8 tasks) — có thể là site demo/test lớn.
- Có **file path bị masked** (tên folder và filename đều là hash) → không dùng tên file để suy đoán loại.

---

## 5. Phân bố Tags (Ground Truth)

| Tag | Số lần xuất hiện | Ghi chú |
|-----|-----------------|---------|
| **22. Khác / Manifest** | 22 | Chiếm 50% — đây là tag của **Folder tasks** (phân loại nhiều loại files cùng lúc) |
| **07. Phiếu kết quả thử nghiệm** | 14 | Tag phổ biến nhất trong QA tasks |
| **19. Ảnh thi công / So ảnh** | 4 | |
| **14. Thông số kỹ thuật thiết bị** | 4 | |
| **17. Hồ sơ điện lực / Công văn** | 3 | |
| **05. Bảng tiến độ thi công** | 2 | |
| **02. Mục lục / Index** | 2 | |
| **18. Bảo hành** | 2 | |
| **06. Bản vẽ hoàn công** | 1 | |
| **01. Bìa / Gáy sách** | 1 | |
| **04. Báo cáo hoàn thành** | 1 | |
| **11. PCS / Power Conditioner** | 1 | |
| **15. Hướng dẫn vận hành** | 1 | |
| **10. Danh sách thiết bị** | 1 | |

**Nhận xét quan trọng:**
- **Tag 22 = "catch-all"**: Folder tasks không thực sự gán một loại cố định — agent phải phân loại từng file riêng lẻ, và tag 22 là label của cả batch (không phải của từng file).
- **Tag 07 (Phiếu thử nghiệm) = tài liệu phổ biến nhất** trong hồ sơ VPP → agent cần giỏi đọc loại tài liệu này.
- **11 tasks có nhiều tags** → task đó chứa files thuộc nhiều loại thư mục khác nhau.

---

## 6. Phân tích 22 QA Tasks

### 6.1 Phân bố theo loại thông tin cần trích xuất

| Loại thông tin | Số tasks | Ví dụ |
|----------------|----------|-------|
| **Giá trị / Số liệu kỹ thuật** | 7 | Điện trở cách điện, công suất định mức, thông số thiết bị |
| **Ngày tháng** | 6 | Ngày phát hành, ngày hoàn thành, ngày hợp đồng |
| **Tên / Nhận dạng** | 5 | Tên công trình, tên sản phẩm, tên nhà sản xuất |
| **Danh sách / Cấu trúc** | 4 | Danh sách mục lục, liệt kê thông số, hạng mục lưu ý |
| **Nội dung / Điều khoản** | 3 | Nội dung hợp đồng, điều khoản bảo hành |
| **Hình ảnh cụ thể** | 3 | Ảnh toàn cảnh, ảnh PCS |

### 6.2 QA Tasks theo từng task

| Task ID (8 ký tự) | #Files | Tags | Thông tin cần extract |
|-------------------|--------|------|-----------------------|
| `1adae939` | 30 | 05, 06, 07 | Tên công trình trong bản vẽ mặt bằng |
| `213d5d92` | 7 | 19 | Ảnh "toàn cảnh" bất động sản |
| `2567ab5b` | 8 | 07, 17 | Ngày phát hành hồ sơ điện lực |
| `2a729f98` | 2 | 02, 07 | Cấu trúc tài liệu từ mục lục |
| `34015ab8` | 21 | 07 | Kết quả đánh giá từng thiết bị (Pass/Fail) |
| `48300f10` | 2 | 01, 07 | Vị trí ghi tên bất động sản trên trang bìa |
| `4b4e1ff1` | 2 | 04 | Ngày hoàn thành từ báo cáo hoàn thành |
| `4f029a29` | 14 | 07, 14, 18 | Thời hạn bảo hành sản phẩm |
| `534e58e9` | 20 | 14 | Tên chính thức sản phẩm từ thông số kỹ thuật |
| `6456ba2d` | 4 | 02, 19 | Danh sách các mục trong mục lục |
| `6b92e96f` | 18 | 07 | Giá trị điện trở cách điện |
| `6ddfa125` | 18 | 07, 11, 14 | Công suất định mức PCS |
| `9083eca0` | 14 | 07, 15 | Thao tác nút bấm chính từ hướng dẫn sử dụng |
| `91339e99` | 11 | 14 | Thông số kỹ thuật các thiết bị chính |
| `98d49b24` | 28 | 05, 07 | Hạng mục lưu ý trong bảng kiểm tra SGS |
| `a2063fcc` | 22 | 07, 10, 19 | Tên nhà sản xuất từng thiết bị |
| `a8158baf` | 9 | 17 | Nội dung ký kết hợp đồng điện lực |
| `ab75a22f` | 9 | 07 | Các giá trị đo có trong tiêu chuẩn không |
| `b00a3da1` | 20 | 19 | Ảnh PCS (bộ điều khiển công suất) |
| `e040aca5` | 20 | 07 | Ngày thực hiện thử nghiệm |
| `f5a18afc` | 70 | 17 | Ngày hợp đồng mua bán điện |
| `fed814d6` | 23 | 07, 18 | Điều khoản miễn trừ và điều khoản đặc biệt bảo hành |

---

## 7. Pattern quan trọng phát hiện được

### 7.1 Folder tasks → tag 22 là "nhiễu"
Tag `22. Khac / Manifest` **không có nghĩa** là tất cả files thuộc thư mục 22. Đây là tag **của task**, không phải của từng file. Khi làm Folder Organisation, agent phải phân loại từng file theo nội dung thực tế của nó vào đúng thư mục (1-22).

### 7.2 Task có nhiều tags = nhiều loại file cùng batch
Khi task có tags `['07', '11', '14']`, nghĩa là trong batch files đó **có file thuộc folder 07, có file thuộc folder 11, có file thuộc folder 14** — agent phải phân loại đúng từng file vào đúng folder tương ứng.

### 7.3 QA tasks luôn bắt đầu bằng "Xác định [loại tài liệu] và [trích xuất thông tin]"
Pattern 2 bước:
1. **Identify:** Tìm đúng file/tài liệu trong batch
2. **Extract:** Trích xuất thông tin cụ thể từ file đó

### 7.4 File path bị mask hoàn toàn
```
Public/VPP0000710_masked_9e5bdb67/03】_masked_3e81ea2b/913d9cfb865b408ab812ca6f68de3ed3.pdf
```
- Site ID: masked một phần (VPP ID + hash)
- Folder: số thứ tự bị giữ (03】) + tên bị mask
- Filename: hoàn toàn là MD5 hash

→ **Không thể dùng tên file để phán đoán loại** — phải đọc nội dung.

### 7.5 Folder source ≠ Folder đích
Files trong thư mục `03】_masked_xxx` của Google Drive **không nhất thiết** thuộc folder 3 của sort_instruction. Đây là thư mục gốc của dữ liệu thô, không phải phân loại chuẩn.

---

## 8. Phân bổ resource count

| Khoảng | Folder tasks | QA tasks |
|--------|-------------|----------|
| 1-5 files | 4 | 4 |
| 6-10 files | 4 | 4 |
| 11-20 files | 8 | 8 |
| 21-30 files | 5 | 5 |
| 31+ files | 1 | 1 |

**Nhận xét:** Phân bổ giống hệt nhau giữa Folder và QA tasks → 44 tasks được xây dựng thành cặp (mỗi site cung cấp 1 batch files → 1 Folder task + 1 QA task).

---

## 9. Implications cho Agent Design

| Phát hiện | Implication |
|-----------|-------------|
| 98.4% là PDF | Tập trung optimize PDF pipeline trước |
| Filename là hash | Phải đọc nội dung file, không dùng tên |
| Tags là per-task, không per-file | Agent phải classify từng file riêng |
| QA pattern: Identify → Extract | Agent cần sub-task 1: classify; sub-task 2: extract |
| Tag 07 xuất hiện trong 14/22 QA tasks | Phiếu thử nghiệm là loại tài liệu phổ biến nhất cần đọc |
| Files trong 1 batch có thể thuộc nhiều loại | Không thể dùng 1 label cho cả batch |
| Dữ liệu tiếng Nhật | Cần LLM/OCR hỗ trợ tiếng Nhật tốt |
