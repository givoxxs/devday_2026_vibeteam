## Input
- Get task:
    - prompt_template: instruction for Q&A
    - resources: [list_file: pdf, excel, doc, image, ...] -> process data -> text_embedding_3 ...
    - tools: tự define
- Đầu vào bao gồm 2 subtask
    - Q&A: Trả lời câu hỏi trong `prompt_template` của payload được trả về. Khi trả lời câu hỏi, agent có thể phải chia ra nhiều subtask khác nhau để đưa ra câu trả lời cuối cùng. Ví dụ: "Xác định hồ sơ điện lực -> kiểm tra ngày phát hành."
    - Folder organization: Phân chia các files trong resources vào 21 thư mục -> lưu local -> submit: though_logs + used_tools.

- 3 phase: 
    1.
    2. O&M -> hỏi lại BTC
    3. Verify: Excutor + Plan + Validator
        - Validator: 
            1. Input (kết quả process data có hợp lệ không)
            2. Validation plan.
            2. Output.



# **Bài toán:**

**Input:**
    - Nhận vào 1 yêu cầu. Một yêu cầu có thể có nhiều yêu cầu nhỏ.
    - Nhận vào danh sách các file dùng để trả lời câu hỏi (doc, pdf, excel, ảnh)
**Output:**
    - Từ yêu cầu đó trả lời câu hỏi tương ứng dựa vào các file đã cung cấp.


# **Phân tích bài toán**

## **Bước 1: Xử lý Prompt Template (User Message)**

**Yêu cầu:**
- Chia nhỏ nhiệm vụ.
- Xác định loại thông tin xác minh. Như trường hợp xác định bảng điện, ảnh gì đó thì cần đưa ra type cần kiểm tra là table, image, remove đi các case thuộc text.

**Công việc:**
1. Bài toán cần phải chia yêu cầu lớn thành các vấn đề nhỏ.
2. Thực hiện các vấn đề **tuần tự/song song**. Việc xác định giúp trả lời đúng vấn đề + tăng tốc độ xử lý

**Ví dụ:**
Ví dụ [Hai công việc + Tuần tự]: 
- Hãy xác định phiếu kết quả thử nghiệm và kiểm tra giá trị điện trở cách điện.
- Dựa trên nội dung tài liệu, hãy xác định phân loại và sắp xếp vào thư mục phù hợp.

## **Bước 2 Xử lý Documents**

**Yêu cầu đầu vào Documents:**
    - **Định dạng:** Pdf, Doc, Image, Excel ....
**Loại văn bản output:**
    - **Định dạng:** JSON
    - **Yêu cầu:**
        - Khi trích xuất tất cả cần có toạ độ / vị trí để tiện validate về sau tránh trường hợp hallucination.
        - Khi trích xuất thì cần có cả loại thông tin vừa trích xuất. (txt, image, dataframe)
        - Với trường hợp bảng sẽ chuyển thành 1 Object với 3 trường tương ứng: Vị trí Cột + Hàng, Giá trị
        - Với trường hợp có hình ảnh thì cần: Lưu hình ảnh, đọc nội dung hình ảnh. 
            - Caption:
            - Summary: 
        - Văn bản bình thường không cần biểu diễn quá nhiều.
    - Context: Lưu context như thế nào? Define các biến ntn?
        - Chia theo type: có thể lưu theo pageindex 

**Công việc**
    - Thực hiện xử lý song song để tránh mất thời gian.
    - Store lại dữ liệu sau khi trích xuất.
    - Xem xét việc stream.


**Thư viện hỗ trợ**
- Docling
- LLM


## **Bước 3 Lên plan xử lý**

- Lên planning cho quá trình xử lý và planning cho quá trình validation.
- Cứ mỗi lần thực hiện hoàn thành 1 yêu cầu thì sẽ có phần đánh giá xem có cần validation không. Nếu cần thì valition sẽ tạo ra 1 plan / bài kiểm tra 

Task A [Validation: 1, 2, 3]

Task B [Validaition 1, 2, 4, 5]


[Sub-Task] -> [Executor] -> [Planning] -> [Tạo Plan] -> Validation Plan
                            [Validation]  -> [Tạo Validation]



[Plan] -> [Executor] -> [n công việc] -> [Hoàn thành A] -> [Gọi Validation] -> [Passed]


-> [Update Plan] 



Lên plan để hoàn thành công việc:

[A]: Thực hiện xác định bảng điện

-> Plan [Gọi tool search -> ] -> [Search vào trong DB]


Agent
Tool [
    - Context:
]
Context:
    - Deps
    - State:
        - Plan
        - Thông tin A, 



## TASK
- Review & analysis data => HUYNH
    - Đọc và review hết data & prompt_template instruction -> tìm insight, pattern để phục vụ cho build plan và define rule ở các bước sau.

- Survey process data: => TOÀN (PDF + IMAGE) & MẠNH (EXCEL + DOC)
    - Xác định pipeline, các tools cần có.
    - Các phương pháp process, thư viện (cho từng loại văn bản khác nhau)
    - Định dạng, lưu những field gì, lưu data nào ?
    - Lưu context như nào để nạp cho Agent?

- Build code with base pipeline (như đã define). => LY

Dl: Tối t4 (25/03)
