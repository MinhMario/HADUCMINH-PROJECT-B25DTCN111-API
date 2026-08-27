# Tổng quan Hệ thống API & Sơ đồ Luồng Xử lý

Tài liệu tổng hợp toàn bộ các API trong dự án Quản lý Chiến dịch Tiếp thị (Marketing Campaign Management System).

---

## 📌 Danh sách các file luồng chi tiết:

1. 📄 **[Luồng API Authentication](file:///f:/New%20folder/.vscode/API/Project/docs/luong_api_auth.md)**
   * `POST /auth/register` - Đăng ký tài khoản
   * `POST /auth/login` - Đăng nhập cấp JWT Tokens
   * `POST /auth/refresh` - Cấp lại Access Token từ Refresh Token

2. 📄 **[Luồng API User](file:///f:/New%20folder/.vscode/API/Project/docs/luong_api_user.md)**
   * `GET /users/me` - Xem thông tin cá nhân
   * `GET /users/` - Danh sách người dùng (Dành cho Admin, phân trang & tìm kiếm)

3. 📄 **[Luồng API Campaign & Member](file:///f:/New%20folder/.vscode/API/Project/docs/luong_api_campaign.md)**
   * `POST /campaigns/` - Tạo mới chiến dịch (Tự động gán Owner)
   * `GET /campaigns/` - Danh sách chiến dịch cá nhân (Owner/Member)
   * `GET /campaigns/{id}` - Xem chi tiết chiến dịch
   * `PUT /campaigns/{id}` - Cập nhật chiến dịch (Owner)
   * `PATCH /campaigns/{id}` - Cập nhật một phần chiến dịch (Owner)
   * `DELETE /campaigns/{id}` - Xóa mềm chiến dịch (Soft Delete - Owner)
   * `POST /campaigns/{id}/members` - Thêm thành viên vào chiến dịch (Owner)
   * `GET /campaigns/{id}/members` - Xem danh sách thành viên chiến dịch
   * `DELETE /campaigns/{id}/members/{user_id}` - Xóa thành viên khỏi chiến dịch (Owner)

4. 📄 **[Luồng API Campaign Task & Comment](file:///f:/New%20folder/.vscode/API/Project/docs/luong_api_campaign_task.md)**
   * `POST /campaigns/{id}/campaign-tasks` - Tạo công việc mới trong chiến dịch
   * `GET /campaigns/{id}/campaign-tasks` - Danh sách công việc (Lọc status, priority, assignee, search, phân trang)
   * `GET /campaign-tasks/{id}` - Chi tiết công việc
   * `PATCH /campaign-tasks/{id}` - Cập nhật công việc (Owner toàn quyền, Assignee chỉ được cập nhật `status`)
   * `DELETE /campaign-tasks/{id}` - Xóa công việc (Owner)
   * `POST /campaign-tasks/{id}/comments` - Viết bình luận vào công việc
   * `GET /campaign-tasks/{id}/comments` - Xem danh sách bình luận (Phân trang)

---

## 🏗️ Sơ đồ Luồng Xử lý Tổng thể (Architecture Flow)

```
[ Client / Web App / Postman ]
             │
             ▼
   [ FastAPI Router Layer ]
   (Xác định Endpoint, Validate Schema Pydantic, HTTP Code)
             │
             ▼
  [ Dependencies & Auth Layer ]
  (Giải mã JWT, Lấy Current User, Check Role Admin/Owner/Member)
             │
             ▼
    [ Service Layer ]
    (Xử lý nghiệp vụ chính, Kiểm tra logic bài toán, Throw Exception 400/403/404)
             │
             ▼
   [ Database Layer ]
   (SQLAlchemy ORM <-> SQLite / MySQL Database)
```

---

## 🚨 Bảng mã lỗi HTTP Status Code chuẩn sử dụng trong bài:
| HTTP Status Code | Ý nghĩa | Mô tả |
| :--- | :--- | :--- |
| `200 OK` | Thành công | Trả về dữ liệu chi tiết / danh sách |
| `201 Created` | Tạo mới thành công | Tạo thành công User, Campaign, Task, Comment |
| `204 No Content` | Xóa thành công | Trả về khi xóa thành viên thành công |
| `400 Bad Request` | Lỗi dữ liệu gửi lên | Trùng email, sai mật khẩu, sai enum status/priority, người được gán không thuộc chiến dịch |
| `401 Unauthorized` | Lỗi xác thực | Chưa đăng nhập, Token hết hạn, Token không hợp lệ |
| `403 Forbidden` | Lỗi phân quyền | Tài khoản bị khóa, người dùng không phải Owner/Member của chiến dịch |
| `404 Not Found` | Không tìm thấy | Campaign/Task/User/Member không tồn tại hoặc đã bị xóa |
