## Phân cấp cấu trúc level của văn bản theo kiểu nested
- Nested các level của văn bản (thuộc phần provisions). Cụ thể, provisions là list chứa các điều, mỗi điều sẽ có 1 key là list_khoan chẳng hạn, chứa các khoản của điều đó, trong mỗi khoản sẽ có key list_điểm chứa các điểm của khoản, ... 
- Với các khoản/ điều có nội dung sửa đổi, sẽ có thêm trường list_modify bao gồm các khoản/ các điều/ điểm được sửa đổi.

- Ví dụ:
[

    {
    "id": "81/2025/QH15_dieu_1_1",
    "level": "dieu",
    "number": "1",
    "title": "Sửa đổi, bổ sung một số điều của Luật Tổ chức Tòa án nhân dân",
    "content": "Điều 1. Sửa đổi, bổ sung một số điều của Luật Tổ chức Tòa án nhân dân",
    "parent_id": null,
    "hierarchy_path": [],
    "list_khoan": [
        {
        "id": "81/2025/QH15_khoan_3_80",
        "level": "khoan",
        "number": "3",
        "title": "Kiến nghị Chánh án Tòa án nhân dân tối cao, Chánh án Tòa án nhân dân cấp",
        "content": "3. Kiến nghị Chánh án Tòa án nhân dân tối cao, Chánh án Tòa án nhân dân cấp tỉnh xem xét, kháng nghị theo thủ tục giám đốc thẩm, tái thẩm b ản án, quyết định của Tòa án nhân dân khu vực, Tòa án nhân dân cấp tỉnh đã có hiệ u lực pháp luật theo quy định của luật.",
        "parent_id": "81/2025/QH15_dieu_59_77",
        "hierarchy_path": [
            "81/2025/QH15_dieu_59_77"
        ],
        "diem": [
            {},
            {},
            {},
            ....
        ]
    },
    {
        {
        "id": "81/2025/QH15_khoan_3_20",
        "level": "khoan",
        "number": "3",
        "title": "Sửa đổi, bổ sung Điều 46 như sau:",
        "content": "3. Sửa đổi, bổ sung Điều 46 như sau: “Điều 46. Nhiệm vụ, quyền hạn của Tòa án nhân dân tối cao Tòa án nhân dân tối cao là cơ quan xét xử cao nhất của nước Cộn g hòa xã hội chủ nghĩa Việt Nam, thực hiện nhiệm vụ, quyền hạn sau đây:",
        "parent_id": "81/2025/QH15_dieu_1_1",
        "hierarchy_path": [
            "81/2025/QH15_dieu_1_1"
        ],
        "list_modify":
        [
            {
                "id": "81/2025/QH15_khoan_1_21",
                "level": "khoan",
                "number": "1",
                "title": "Giám đốc thẩm, tái thẩm bản án, quyết định của các Tòa án đã  có hiệu lực",
                "content": "1. Giám đốc thẩm, tái thẩm bản án, quyết định của các Tòa án đã  có hiệu lực pháp luật bị kháng nghị theo quy định của luật;",
                "parent_id": "81/2025/QH15_dieu_1_1",
                "hierarchy_path": [
                    "81/2025/QH15_dieu_1_1"
                ]
            },
            ...
        ]
    },
    }
    ]
    },
    
]