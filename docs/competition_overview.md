# VPP AI Agent Challenge — Tổng quan cuộc thi

**Chủ đề:** *From AI to AX* (Từ Ứng dụng AI đến Chuyển đổi AI)
**Tổ chức:** TAS Design Group
**Sự kiện kết thúc:** DevDay2026 — 18/04/2026

---

## 1. Bối cảnh và Mục tiêu

| # | Mục tiêu | Mô tả |
|---|----------|-------|
| 1 | **Xây dựng Case Model cho AX** | Hướng tới dịch chuyển từ "Ứng dụng AI" sang "AI Transformation (AX)" thông qua hệ thống quản lý xây dựng VPP (Virtual Power Plant) được điều khiển bởi AI. |
| 2 | **Tự động hóa tổ chức dữ liệu** | Thiết kế vòng lặp AI tự động tổ chức dữ liệu vận hành (nhật ký kiểm tra, v.v.), ngăn chặn GIGO (Garbage In Garbage Out) và nâng cao tiện ích. |
| 3 | **Phát hiện và nuôi dưỡng nhân tài AX** | Đào tạo kỹ sư kết hợp kỹ năng phát triển AI với hiểu biết sâu về vận hành kinh doanh năng lượng. |

---

## 2. Về Dữ liệu

- **Multi-modal As-built Documents:** Dữ liệu bao gồm các file PDF, hình ảnh, và Excel rải rác. AI Agent lấy dữ liệu này từ Google Drive.
- **Ẩn thông tin bảo mật:** Tên công ty và tên cá nhân đã được redact trước.
- **Public và Private Data:**
  - **Public Data:** Dùng để phát triển và thử nghiệm.
  - **Private Data:** Dùng cho đánh giá cuối cùng (final evaluation).

---

## 3. Nhiệm vụ của Người tham gia

Xây dựng một **Autonomous AI Agent** vận hành qua **3 giai đoạn (phases)** trên simulator được cung cấp:

### Phase 1 — Observability (Quan sát)
Tự động gắn tag và trích xuất dữ liệu thiết yếu từ dữ liệu tài sản rải rác như PDF và hình ảnh.

### Phase 2 — Action Generation (Tạo hành động)
Hiểu các quy định và dữ liệu để lên kế hoạch và thực thi các hành động vận hành & bảo trì (O&M) chính xác.

### Phase 3 — Verifiability (Kiểm chứng)
Agent tự đánh giá tính hợp lệ của kế hoạch và hành động của mình để tiến hành phù hợp.

---

## 4. Quy tắc và Đánh giá

### Cách thức nộp bài
- Các đội nộp một **AI Agent có thể thực thi được**.
- TasDG sẽ chạy agent trên simulator và đánh giá kết quả.
- **2 lần nộp:**
  - **Lần 1 (Pre-submission):** Kiểm tra test case.
  - **Lần 2 (Final submission):** Đánh giá chính thức.

### Hồ sơ cần nộp (Deliverables)
1. Source code của executable agent
2. Presentation slides

---

## 5. Tiêu chí chấm điểm

### Đánh giá định lượng (3 trục)

| Trục | Tiêu chí | Mô tả |
|------|----------|-------|
| **Accuracy** | Precision & Meaning match | Độ chính xác và khớp nghĩa của câu trả lời |
| **Efficiency** | Latency & Tokens | Tốc độ phản hồi và số lượng token sử dụng |
| **Robustness** | Error handling | Khả năng xử lý lỗi |

### Đánh giá định tính (Qualitative Evaluation)

| Tiêu chí | Ý nghĩa |
|----------|---------|
| **Planning** | Khả năng lập kế hoạch của agent |
| **Self-correction** | Khả năng tự sửa lỗi |
| **Memory (RAG)** | Sử dụng bộ nhớ và Retrieval-Augmented Generation |
| **Monitoring** | Giám sát quá trình thực thi |
| **Safety** | An toàn trong các hành động |

> **Lưu ý:** `correct` và `score` luôn trả về `0` tại thời điểm nộp. Chấm điểm chính thức được thực hiện theo batch sau khi cuộc thi kết thúc.

---

## 6. Lịch trình

| Ngày | Sự kiện |
|------|---------|
| **29/03 – 03/04/2026** | Mid-term Review (Đánh giá giữa kỳ) |
| **12/04/2026 (CN) 23:59** | **Deadline nộp bài cuối** |
| **18/04/2026 (T7)** | **Công bố kết quả tại DevDay2026** |

---

## 7. Thông tin khác

- **API Key:** OpenAI API key được cung cấp bởi ban tổ chức cho agent của các đội.
- **Data Provider:** Hệ thống cung cấp dữ liệu được giải thích bởi Lam-san.
- **Công cụ liên lạc:** Sử dụng công cụ giao tiếp với ban tổ chức theo hướng dẫn riêng.
