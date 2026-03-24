# Hiểu đề bài — VPP AI Agent Challenge

> Tổng hợp từ phân tích của đội thi

---

## Bài toán tổng quát

**Input:** Một yêu cầu (có thể bao gồm nhiều yêu cầu nhỏ) + danh sách files đính kèm (PDF, Excel, Doc, Image).

**Output:** Trả lời câu hỏi hoặc phân loại file dựa trên nội dung tài liệu đã cung cấp.

---

## Hai loại Sub-task trong mỗi Phase

### Sub-task 1: Question Answering (Q&A)
- Đọc `prompt_template` → phân tích yêu cầu → chia nhỏ thành các sub-question → trả lời từng phần → tổng hợp câu trả lời cuối.
- **Ví dụ:** "Xác định hồ sơ điện lực → kiểm tra ngày phát hành."
- Agent có thể xử lý tuần tự hoặc song song tuỳ thuộc vào dependency giữa các sub-question.

### Sub-task 2: Folder Organisation
- Phân loại từng file trong `resources` vào 1 trong 21 thư mục theo quy tắc đã định nghĩa.
- Submit: `answers = []` (empty), kèm `thought_log` chi tiết lý luận + `used_tools`.
- Evaluation xem xét **chất lượng reasoning**, không chỉ kết quả phân loại.

---

## Các Cluster câu hỏi thực tế (từ phân tích data)

| Cluster | Chủ đề | Ví dụ câu hỏi |
|---------|--------|---------------|
| **1** | Phân loại & sắp xếp thư mục | "Xác định phân loại dựa trên nội dung tài liệu và sắp xếp vào thư mục phù hợp." |
| **2** | Hồ sơ điện lực & hợp đồng | "Xác định hồ sơ điện lực và kiểm tra ngày phát hành." / "Xác nhận ngày hợp đồng mua bán điện." |
| **3** | Phiếu kết quả thử nghiệm | "Kiểm tra giá trị điện trở cách điện." / "Xác nhận ngày thực hiện thử nghiệm." |
| **4** | Thông số kỹ thuật & thiết bị | "Kiểm tra thời hạn bảo hành." / "Xác nhận công suất định mức PCS." / "Liệt kê thông số thiết bị chính." |
| **5** | Tài liệu hoàn công & bản vẽ | "Xác định bản vẽ mặt bằng tổng thể." / "Xác định báo cáo hoàn thành công trình." |
| **6** | Ảnh & mục lục | "Tìm ảnh toàn cảnh bất động sản." / "Xác định file mục lục và kiểm tra cấu trúc tài liệu." |

**Nhận xét:** Cluster 1 (Folder Organisation) chiếm tỷ lệ lớn nhất → đây là task cốt lõi cần tối ưu.

---

## Yêu cầu xử lý Documents

### Input formats
- PDF, Doc, Image (PNG/JPG), Excel

### Output format (JSON chuẩn hoá)
Khi trích xuất cần đảm bảo:
- **Toạ độ / vị trí** của từng phần thông tin → phục vụ validation, tránh hallucination.
- **Loại thông tin** vừa trích xuất: `text`, `image`, `table/dataframe`.
- **Với bảng:** Object gồm `{position: {row, col}, value}`.
- **Với hình ảnh:** Lưu ảnh gốc + `caption` + `summary` (đọc nội dung ảnh bằng LLM/vision model).
- **Với text thuần:** Không cần biểu diễn quá phức tạp.
- Có thể lưu context theo `page_index`.

### Cấu trúc JSON tham khảo (nested theo level)
```json
{
  "file_path": "site_01/electrical/report.pdf",
  "file_type": "pdf",
  "pages": [
    {
      "page_index": 1,
      "elements": [
        {
          "type": "text",
          "content": "...",
          "bbox": [x1, y1, x2, y2]
        },
        {
          "type": "table",
          "bbox": [x1, y1, x2, y2],
          "data": [
            {"row": 0, "col": 0, "value": "..."}
          ]
        },
        {
          "type": "image",
          "bbox": [x1, y1, x2, y2],
          "caption": "...",
          "summary": "..."
        }
      ]
    }
  ]
}
```

---

## Ba Phase của Simulation

| Phase | Tên | Mô tả |
|-------|-----|-------|
| **1** | Observability | Trích xuất + gắn tag dữ liệu từ PDF, ảnh, tài liệu rải rác. |
| **2** | Action Generation | Hiểu quy định + data → lập kế hoạch O&M → thực thi. (Cần hỏi thêm BTC về nội dung cụ thể) |
| **3** | Verifiability | Agent tự đánh giá tính hợp lệ của kế hoạch + kết quả. Gồm: Executor + Planner + Validator. |

### Chi tiết Phase 3 — Verifiability
```
[Sub-Task] → [Executor] → [Planner] → [Tạo Plan] → Validation Plan
                          [Validator] → [Tạo Validation Checklist]

[Plan] → [Executor] → [n công việc] → [Hoàn thành A] → [Gọi Validator] → [Passed/Failed]
                                                                          → [Update Plan nếu Failed]
```

Validator kiểm tra 3 tầng:
1. **Input validation:** Kết quả process data có hợp lệ không?
2. **Plan validation:** Kế hoạch thực thi có đúng không?
3. **Output validation:** Kết quả đầu ra có đúng không?

---

## Phân công đội (từ design.md)

| Người | Task | Deadline |
|-------|------|----------|
| **HUỲNH** | Review & analysis data — đọc hết data + prompt_template, tìm insight/pattern phục vụ build plan | Tối T4 (25/03) |
| **TOÀN** | Survey process data: PDF + IMAGE | Tối T4 (25/03) |
| **MẠNH** | Survey process data: EXCEL + DOC | Tối T4 (25/03) |
| **LÝ** | Build code base pipeline | Tối T4 (25/03) |
