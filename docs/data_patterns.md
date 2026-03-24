# Data Patterns — Insight để Build Agent

> Chi tiết các pattern từ data, trực tiếp phục vụ thiết kế Agent

---

## Pattern 1: QA Task — Cấu trúc 2 bước cố định

Tất cả 22 QA tasks đều có cấu trúc:

```
"Xác định [TÊN LOẠI TÀI LIỆU] và [HÀNH ĐỘNG TRÍCH XUẤT]"
```

### Bước 1: Identify (Xác định loại tài liệu)

| Từ khoá trong prompt | Loại tài liệu cần tìm | Folder tương ứng |
|---------------------|----------------------|-----------------|
| "phiếu kết quả thử nghiệm" | Test Report | 07 |
| "hồ sơ điện lực" / "hồ sơ thủ tục điện lực" | Utility Documents | 17 |
| "bản vẽ hoàn công" / "bản vẽ mặt bằng tổng thể" | Construction Drawings | 06 |
| "tệp bìa" | Spine/Cover | 01 |
| "tệp mục lục" / "tệp mục lục・chỉ mục" | Table of Contents | 02 |
| "báo cáo hoàn thành công trình" | Completion Report | 04 |
| "bản thông số kỹ thuật PCS" | PCS/Power Conditioners | 11 |
| "bản thông số kỹ thuật thiết bị" | Equipment Specs | 14 |
| "danh sách thiết bị" | Equipment Config/List | 10 |
| "hướng dẫn sử dụng" | User/Operation Manuals | 15 |
| "phiếu bảo hành" | Warranties | 18 |
| "tệp ảnh" | Construction Photos | 19 |
| "bảng kiểm tra hoàn công SGS" | Self-Inspection / Schedule | 05/08 |
| "các loại tài liệu đặc tả" | Equipment Specs | 14 |

### Bước 2: Extract (Loại thông tin cần lấy)

| Từ khoá trong prompt | Loại thông tin | Gợi ý extract strategy |
|---------------------|----------------|------------------------|
| "kiểm tra ngày phát hành" | Date | Tìm field ngày, header, footer |
| "xác nhận ngày hợp đồng" | Date | Tìm trong bảng ký kết |
| "đọc thông tin ngày hoàn thành dưới định dạng thẻ" | Date (structured) | Extract dạng tag/field |
| "kiểm tra kết quả đánh giá" | Pass/Fail per device | Đọc bảng kết quả |
| "kiểm tra giá trị điện trở cách điện" | Numeric value (MΩ) | Extract số từ bảng |
| "kiểm tra công suất định mức" | Numeric (kW/MW) | Spec table |
| "kiểm tra xem các giá trị đo có nằm trong tiêu chuẩn" | Boolean / threshold | So sánh giá trị vs tiêu chuẩn |
| "xác nhận tên chính thức của sản phẩm" | String (product name) | Header của spec sheet |
| "kiểm tra tên nhà sản xuất" | String list | Table of devices |
| "kiểm tra cấu trúc tài liệu" | List of items | Table of contents |
| "lập danh sách các mục" | List | TOC extraction |
| "kiểm tra vị trí ghi tên bất động sản" | Location description | Layout analysis |
| "xác nhận nội dung ký kết hợp đồng" | Text summary | Full text extraction |
| "kiểm tra các điều khoản miễn trừ và điều khoản đặc biệt" | Clause text | Section extraction |
| "kiểm tra thời hạn bảo hành" | Duration (years/months) | Warranty table |
| "kiểm tra các thao tác nút bấm chính" | List of operations | Manual extraction |
| "liệt kê thông số kỹ thuật của các thiết bị chính" | Spec table | Multi-device specs |
| "kiểm tra các hạng mục lưu ý" | List of notes | Inspection notes |
| "tìm ảnh cho thấy toàn cảnh" | Image identification | Caption/content matching |
| "trích xuất ảnh của bộ điều khiển công suất" | Image identification | Equipment visual search |
| "kiểm tra việc ghi tên công trình" | String (project name) | Drawing title block |

---

## Pattern 2: Folder Organisation — Batch phân loại

**22 Folder tasks** đều có prompt dạng:
> "Dựa trên nội dung tài liệu, hãy xác định phân loại và sắp xếp vào thư mục phù hợp."

Đặc điểm:
- Mỗi task có **2-70 files** (avg ~17 files)
- Files trong 1 task **thường đến từ nhiều folder nguồn** (2-6 folders khác nhau)
- **Không có câu hỏi cụ thể** → submit `answers = []`, mọi lý luận vào `thought_log`
- Evaluation đánh giá **quality of reasoning** trong `thought_log`

**thought_log cần chứa:**
```
Cho mỗi file:
- File: <filename>
- Nội dung chính: <tóm tắt ngắn>
- Loại tài liệu: <tên tiếng Nhật>
- Folder đề xuất: <số>. <tên folder>
- Lý do: <giải thích tại sao>
```

---

## Pattern 3: Tag 07 — Tài liệu xuất hiện nhiều nhất

**Phiếu kết quả thử nghiệm / Bang kiem tra (Folder 07)** xuất hiện trong **14/22 QA tasks**. Đây là loại tài liệu quan trọng nhất.

### Đặc điểm Phiếu thử nghiệm điện mặt trời:
- Tiếng Nhật: 試験成績書・検査表
- Nội dung: Bảng đo các thông số kỹ thuật (điện trở cách điện, điện trở tiếp địa, v.v.)
- Kết quả: PASS / FAIL / ○ / × cho từng thiết bị
- Thường có: ngày thực hiện, tên thiết bị, mã thiết bị, giá trị đo, giá trị tiêu chuẩn

### Các sub-questions thường gặp với folder 07:
```
- Kết quả đánh giá của thiết bị X là gì? → đọc cột "判定" (judgment)
- Giá trị điện trở cách điện là bao nhiêu? → đọc cột giá trị đo (MΩ)
- Ngày thực hiện thử nghiệm? → header/footer của phiếu
- Các giá trị có trong tiêu chuẩn không? → so sánh giá trị đo với giá trị chuẩn
```

---

## Pattern 4: Folder 17 — Hồ sơ điện lực có ngày tháng

**3 QA tasks về folder 17** đều hỏi về ngày/hợp đồng:
- "Kiểm tra ngày phát hành"
- "Xác nhận nội dung ký kết hợp đồng"
- "Xác nhận ngày hợp đồng mua bán điện"

**Đặc điểm tài liệu điện lực:**
- Thường là văn bản hành chính tiếng Nhật
- Có ngày tháng rõ ràng (năm月日)
- Hợp đồng mua bán điện: 電力売買契約
- Grid connection: 系統連系

---

## Pattern 5: Ảnh (Folder 19) — Nhận dạng nội dung ảnh

**3 QA tasks về folder 19** đều yêu cầu **xác định ảnh cụ thể**:
- "Tìm ảnh toàn cảnh (全景)"
- "Trích xuất ảnh của PCS (bộ điều khiển công suất / パワーコンディショナ)"

**Lưu ý:** Dù file type là `pdf`, nhưng đây là **PDF chứa ảnh** (photo album PDF). Cần:
1. Extract ảnh từ PDF
2. Chạy caption/summary bằng Vision LLM
3. Match với keyword trong prompt ("全景", "パワーコンディショナ")

---

## Pattern 6: Files cùng 1 folder nguồn → không nhất thiết cùng loại

Ví dụ task `65302e5f`: 20 files, tất cả đến từ folder `03】_masked` và `04】_masked`, nhưng tag là `22. Khác / Manifest`.

Folder số nguồn trong file path (03, 04, 07...) **không tương ứng** với folder đích trong sort_instruction. Đây là số thứ tự folder của khách hàng (lộn xộn), không phải chuẩn.

---

## Pattern 7: Batch size tương quan với task type

| Task type | Small batch (≤5) | Medium (6-20) | Large (>20) |
|-----------|-----------------|---------------|-------------|
| Folder org | 4 tasks | 12 tasks | 6 tasks |
| QA | 4 tasks | 12 tasks | 6 tasks |

Hoàn toàn đối xứng → mỗi batch files được dùng cho cả Folder task lẫn QA task từ cùng site.

---

## Pattern 8: Prompt tiếng Nhật vs tiếng Việt — giống hệt về nghĩa

| Tiếng Nhật | Tiếng Việt |
|-----------|-----------|
| 書類の内容に基づき分類を特定し、適切なフォルダへ配置せよ。 | Dựa trên nội dung tài liệu, hãy xác định phân loại và sắp xếp vào thư mục phù hợp. |
| 試験成績書を特定し、機器ごとの判定結果を確認せよ。 | Xác định phiếu kết quả thử nghiệm và kiểm tra kết quả đánh giá của từng thiết bị. |

Agent có thể dùng **prompt tiếng Việt** (`task_info_vi.json`) để process — dễ handle hơn.

---

## Checklist cho Agent khi nhận task

```
1. Load task_info (prompt + resource list)
2. Detect task type:
   IF prompt contains "sắp xếp vào thư mục" AND no specific extraction request:
       → FOLDER ORGANISATION task
   ELSE:
       → QA task
       → Parse: which document type to find? + what info to extract?

3. Process documents (parallel):
   FOR each resource:
       → Download file
       → Extract content (text + tables + images)
       → Generate summary + document_type_guess

4. Execute:
   IF FOLDER task:
       → For each file: classify into 1 of 21 folders
       → Build detailed thought_log
       → answers = []
   IF QA task:
       → Sub-task 1: Identify the target document(s) using extracted summary
       → Sub-task 2: Extract specific info from identified document
       → Format answer as list of strings

5. Validate:
   → Check extracted info makes sense (date format, numeric range, etc.)
   → Check folder assignment matches document content

6. Submit: answers + thought_log + used_tools
```

---

## Từ điển thuật ngữ kỹ thuật hay gặp

| Tiếng Nhật | Tiếng Việt | Tiếng Anh |
|-----------|-----------|-----------|
| 試験成績書 | Phiếu kết quả thử nghiệm | Test Report |
| 絶縁抵抗 | Điện trở cách điện | Insulation Resistance |
| 接地抵抗 | Điện trở tiếp địa | Grounding Resistance |
| パワーコンディショナ (PCS) | Bộ biến tần | Power Conditioner |
| モジュール | Module pin NLMT | Solar Module |
| 系統連系 | Đấu nối lưới điện | Grid Connection |
| 竣工図面 | Bản vẽ hoàn công | As-built Drawing |
| 物件名 | Tên công trình / bất động sản | Property/Project Name |
| 全景 | Toàn cảnh | Overall View |
| 判定 | Kết quả đánh giá | Judgment/Pass-Fail |
| 保証書 | Giấy bảo hành | Warranty Certificate |
| 目次 | Mục lục | Table of Contents |
| 電力売買契約 | Hợp đồng mua bán điện | Power Purchase Agreement |
| スマートロガー | Smart Logger | Smart Logger |
| 工事工程表 | Bảng tiến độ thi công | Construction Schedule |
