# VPP AI Agent Competition — API Reference

Tài liệu này mô tả cách tương tác với server simulation của cuộc thi.

---

## Tổng quan (Overview)

Simulator trình bày cho agent của bạn một chuỗi tasks qua nhiều phases. Mỗi task cung cấp một tập files để phân tích và một prompt mô tả việc cần làm. Agent phải fetch task, xử lý files, và submit câu trả lời trước khi task tiếp theo được phát.

**Vòng lặp chính:**

```
POST /sessions          ← bắt đầu session mới (hoặc resume bằng session_id)
  └─ loop:
       GET  /tasks/next ← nhận task tiếp theo (404 khi tất cả phases hoàn thành)
       POST /submissions ← nộp câu trả lời cho task đó
```

---

## Xác thực (Authentication)

### Bước 1 — Lấy API Key
API key được cung cấp bởi ban tổ chức. **Giữ bí mật.**

### Bước 2 — Tạo hoặc Resume Session

**Tạo session mới** (không cần body):
```http
POST /sessions
X-API-Key: <your-api-key>
```

**Resume session cũ** (truyền `session_id` đã lưu):
```http
POST /sessions
X-API-Key: <your-api-key>
Content-Type: application/json

{
  "session_id": "3fa85f64-..."
}
```

### Bảng trạng thái response

| Scenario | Status |
|----------|--------|
| Không có `session_id` trong body | `201` — new session created |
| `session_id` hợp lệ, còn tasks | `200` — session resumed |
| `session_id` không tìm thấy hoặc sai agent | `404` |
| `session_id` đã hoàn thành | `409` |

### Response 201 — Session mới được tạo
```json
{
  "session_id": "3fa85f64-...",
  "agent_id":   "9b2e1c00-...",
  "access_token": "<JWT>",
  "token_type": "bearer",
  "expires_in": 3600
}
```

> **Quan trọng:** Lưu `session_id` và `access_token`. Token hợp lệ trong `expires_in` giây (mặc định 60 phút). Phải truyền Bearer token cho mọi request tiếp theo.
> Nếu token hết hạn giữa chừng, gọi lại `POST /sessions` với `session_id` — tiến trình được bảo toàn.

---

## Endpoints

### GET /tasks/next

Trả về task tiếp theo cho session. Tasks được sắp xếp theo phase (tăng dần). Trong mỗi phase, task **Question-Answering luôn được trả về trước** task Folder-Organisation.

**Request:**
```http
GET /tasks/next
Authorization: Bearer <access_token>
```

**Response 200:**
```json
{
  "task_id": "a1b2c3d4-...",
  "prompt_template": "...",
  "resources": [
    {
      "file_path": "site_01/electrical/report.pdf",
      "file_type": "pdf",
      "token": "<signed-download-jwt>"
    }
  ]
}
```

| Field | Mô tả |
|-------|-------|
| `task_id` | Định danh duy nhất — bao gồm trong submission. |
| `prompt_template` | Hướng dẫn agent phải thực hiện. |
| `resources` | Các file agent cần đọc. Mỗi `token` là JWT để download file qua `GET /download?token=<token>`. Token hết hạn sau ~1 giờ. |

**Response 404:** Tất cả phases đã hoàn thành — simulation kết thúc.

---

### POST /submissions

Nộp câu trả lời cho task hiện tại.

**Request:**
```http
POST /submissions
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "session_id": "3fa85f64-...",
  "task_id":    "a1b2c3d4-...",
  "answers":    ["ANS value_1", "ANS value_2"],
  "thought_log": "I read file X and found ...",
  "used_tools":  ["file_reader", "ocr"]
}
```

| Field | Required | Mô tả |
|-------|----------|-------|
| `session_id` | Yes | Phải khớp với session trong Bearer token. |
| `task_id` | Yes | `task_id` nhận từ `GET /tasks/next`. |
| `answers` | Yes | Danh sách các string trả lời (xem Answer format). |
| `thought_log` | No | Trace lý luận dạng free-text — dùng cho đánh giá insight. |
| `used_tools` | No | Tên các tools agent đã dùng để giải task. |

**Response 200:**
```json
{
  "task_id": "a1b2c3d4-...",
  "session_id": "3fa85f64-...",
  "total_files": 2,
  "correct": 0,
  "score": 0.0,
  "details": []
}
```

> **Lưu ý:** `correct` và `score` luôn là `0` tại thời điểm nộp. Chấm điểm cuối được thực hiện theo batch sau khi cuộc thi kết thúc.

---

## Downloading Files

Mỗi resource trong task chứa field `token` — JWT xác định file. Fetch nội dung file qua:

```http
GET /download?token=<signed-download-jwt>
Authorization: Bearer <access_token>
```

Token hết hạn sau ~1 giờ. Nếu hết hạn, gọi lại `GET /tasks/next` — server cấp token mới.

**Python example:**
```python
for resource in task["resources"]:
    file_resp = client.get(
        "/download",
        params={"token": resource["token"]},
        headers=auth_headers,
    )
    file_resp.raise_for_status()
    file_bytes = file_resp.content
    # process file_bytes ...
```

---

## Answer Format

`answers` là danh sách các plain string (có thể nộp chỉ một answer).

**Example:**
```json
["Panel_A", "Panel_B"]
```

---

## Task Types

Hai loại task xuất hiện trong mỗi phase, mỗi site:

### 1. Question Answering
Agent đọc các files được cung cấp và trả lời các câu hỏi cụ thể từ `prompt_template`. Nộp câu trả lời trong field `answers` dưới dạng danh sách string.

### 2. Folder Organisation
Agent xác định folder/category đúng cho mỗi file được cung cấp. Việc tổ chức folder có thể được xử lý locally. Có thể nộp list rỗng `[]` cho `answers` vì không có câu hỏi tường minh — thay vào đó, lý luận và phân loại folder phải được mô tả trong field `thought_log` vì evaluation cũng xem xét chất lượng reasoning trace của agent.

> **Thứ tự:** Trong một site, task Question-Answering luôn được phát **trước** task Folder-Organisation.

---

## Error Reference

| Status | Ý nghĩa |
|--------|---------|
| `401 Unauthorized` | API key bị thiếu hoặc không hợp lệ (trên `POST /sessions`). |
| `403 Forbidden` | `session_id` trong body không khớp token, hoặc download token không hợp lệ/hết hạn/không thuộc session của bạn. |
| `404 Not Found` | Không còn task nào (simulation hoàn thành), hoặc `session_id` không tìm thấy. |
| `409 Conflict` | Bạn đã nộp một task đã hoàn thành, hoặc `session_id` thuộc session đã kết thúc. |
| `503 Service Unavailable` | Server chưa được khởi tạo — thử lại sau. |

---

## Important Constraints

- **Explicit session resume:** Để resume session chưa hoàn thành, truyền `{"session_id": "<your-session-id>"}` trong body của `POST /sessions`. Không có nó, session mới luôn được tạo (`201`).
- **No re-submission:** Một task đã nộp, nộp lại `task_id` đó sẽ trả về `409`. Chuyển sang task tiếp theo.
- **Resource token expiry:** Download token trong `resources` hết hạn sau ~1 giờ. Gọi lại `GET /tasks/next` để lấy token mới.
- **Bearer token expiry:** Bearer token hết hạn sau `expires_in` giây. Gọi `POST /sessions` với `session_id` để lấy token mới và tiếp tục từ chỗ dừng.

---

## Complete Example (Python)

```python
import httpx

BASE_URL = "http://<server-host>"
API_KEY  = "<your-api-key>"

with httpx.Client(base_url=BASE_URL) as client:
    # 1. Start hoặc resume session
    session_id = None  # set session_id đã lưu để resume
    body = {"session_id": session_id} if session_id else {}
    resp = client.post("/sessions", headers={"X-API-Key": API_KEY}, json=body)
    resp.raise_for_status()
    data = resp.json()
    session_id   = data["session_id"]
    access_token = data["access_token"]
    auth_headers = {"Authorization": f"Bearer {access_token}"}

    # 2. Main loop
    while True:
        task_resp = client.get("/tasks/next", headers=auth_headers)

        # Refresh token nếu hết hạn
        if task_resp.status_code == 401:
            refresh = client.post("/sessions",
                headers={"X-API-Key": API_KEY},
                json={"session_id": session_id})
            refresh.raise_for_status()
            access_token = refresh.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {access_token}"}
            task_resp = client.get("/tasks/next", headers=auth_headers)

        if task_resp.status_code == 404:
            print("Simulation complete.")
            break
        task_resp.raise_for_status()
        task = task_resp.json()

        # Download và xử lý files
        for resource in task["resources"]:
            file_resp = client.get("/download",
                params={"token": resource["token"]},
                headers=auth_headers)
            file_resp.raise_for_status()
            file_bytes = file_resp.content
            # --- Xử lý file_bytes tại đây ---

        # --- Logic agent của bạn ---
        answers    = ["example_answer"]
        thought_log = "Reasoned about the files..."
        used_tools  = ["file_reader"]

        # Submit
        sub_resp = client.post("/submissions", headers=auth_headers, json={
            "session_id":  session_id,
            "task_id":     task["task_id"],
            "answers":     answers,
            "thought_log": thought_log,
            "used_tools":  used_tools,
        })
        sub_resp.raise_for_status()
```
