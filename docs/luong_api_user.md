# Luồng xử lý API User (Người dùng)

Tài liệu chi tiết luồng xử lý (Workflow/Sequence) cho nhóm API **User**.

---

## 1. GET `/users/me` - Lấy thông tin cá nhân của người dùng đang đăng nhập

### 🎯 Mục đích:
Trả về thông tin hồ sơ của chính người dùng đang thực hiện request dựa trên Access Token được gửi kèm.

### 📥 Đầu vào (Request):
* **Header:** `Authorization: Bearer <access_token>` (Bắt buộc)

### 🔄 Các bước xử lý (Workflow):
1. **Xác thực Token qua Dependency (`dependencies/dep.py` -> `get_current_user`):**
   * Tách Token từ header `Authorization`.
   * Giải mã Token kiểm tra tính hợp lệ và thời gian hết hạn (`decode_access_token`).
   * Kiểm tra loại token `type == "access"`.
   * Lấy `user_id` từ token payload, truy vấn CSDL bảng `users`.
   * **Nếu Token sai/hết hạn/user không tồn tại:** Bắn lỗi `UnauthorizedException` (`401 Unauthorized`).
   * **Nếu `is_active == False`:** Bắn lỗi `ForbiddenException` (`403 Forbidden`).
2. **Router (`router/user.py`):**
   * Nhận đối tượng `current_user` từ dependency `get_current_user`.
3. **Trả về kết quả:**
   * Trả về trực tiếp thông tin `current_user` dưới dạng `UserResponse` (`id`, `full_name`, `email`, `role`, `is_active`, `created_at`).
   * HTTP Status Code: `200 OK`.

---

## 2. GET `/users/` - Danh sách người dùng (Phân trang, Tìm kiếm, Phân quyền Admin)

### 🎯 Mục đích:
Cho phép tài khoản có quyền **ADMIN** xem danh sách toàn bộ người dùng trong hệ thống với các tính năng phân trang, tìm kiếm và lọc.

### 📥 Đầu vào (Request):
* **Header:** `Authorization: Bearer <access_token>` (Bắt buộc)
* **Query Parameters:**
  * `page`: int (Default = 1)
  * `size`: int (Default = 10)
  * `sort_by`: string (id / full_name / email / role, Default = "id")
  * `order`: string (asc / desc, Default = "asc")
  * `search`: string | None (tìm tương đối theo `full_name` hoặc `email`)
  * `is_active`: bool | None (lọc theo trạng thái hoạt động)

### 🔄 Các bước xử lý (Workflow):
1. **Kiểm tra quyền ADMIN (`dependencies/dep.py` -> `require_admin`):**
   * Lấy `current_user` từ `get_current_user`.
   * Kiểm tra `current_user.role == "ADMIN"`.
   * **Nếu không phải ADMIN:** Bắn lỗi `ForbiddenException` (`403 Forbidden`) với message `"Chỉ Admin mới có quyền truy cập"`.
2. **Router & Service (`service/service.py` -> `get_users`):**
   * Tạo query cơ sở: `db.query(User)`.
3. **Lọc tìm kiếm (`search`):**
   * Nếu có `search`, áp dụng lọc ilike: `(User.full_name.ilike('%search%')) | (User.email.ilike('%search%'))`.
4. **Lọc trạng thái (`is_active`):**
   * Nếu `is_active` được truyền vào (`True`/`False`), thêm điều kiện `filter(User.is_active == is_active)`.
5. **Sắp xếp (`apply_sorting`):**
   * Xác định cột cần xếp (`id`, `full_name`, `email`, `role`) và thứ tự (`asc` / `desc`).
6. **Phân trang (`paginate`):**
   * Đếm tổng số bản ghi (`total`).
   * Tính tổng số trang (`total_pages = ceil(total / size)`).
   * Lấy danh sách item (`query.offset((page - 1) * size).limit(size).all()`).
7. **Trả về kết quả:**
   * Response Model: `PaginatedResponse[UserResponse]` (`total`, `page`, `size`, `total_pages`, `items`).
   * HTTP Status Code: `200 OK`.
