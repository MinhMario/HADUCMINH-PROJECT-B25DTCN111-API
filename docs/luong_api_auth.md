# Luồng xử lý API Authentication (Xác thực)

Tài liệu chi tiết luồng xử lý (Workflow/Sequence) cho nhóm API **Authentication**.

---

## 1. POST `/auth/register` - Đăng ký tài khoản người dùng

### 🎯 Mục đích:
Tạo tài khoản người dùng mới vào hệ thống.

### 📥 Đầu vào (Request):
* **Body (JSON):** `UserCreate`
  * `full_name`: string (bắt buộc)
  * `email`: string (đúng định dạng email, bắt buộc)
  * `password`: string (tối thiểu 6 ký tự, bắt buộc)

### 🔄 Các bước xử lý (Workflow):
1. **Router (`router/auth.py`):** Nhận request từ client, inject `db: Session` và gọi `create_user(user, db)`.
2. **Kiểm tra trùng lặp email (`service/service.py`):**
   * Tìm kiếm trong bảng `users` xem email đã tồn tại chưa (`User.email == user.email`).
   * **Nếu đã tồn tại:** Bắn lỗi `BadRequestException` (`400 Bad Request`) với message `"Email đã bị trùng"`.
3. **Mã hóa mật khẩu & khởi tạo User:**
   * Gọi hàm `hash_pass(password)` (sử dụng `passlib.context` với thuật toán `bcrypt`).
   * Đặt các giá trị mặc định: `role = "USER"`, `is_active = True`.
4. **Lưu dữ liệu:**
   * Thêm đối tượng `User` mới vào cơ sở dữ liệu (`db.add`, `db.commit`, `db.refresh`).
5. **Trả về kết quả:**
   * Mẫu dữ liệu trả về `UserResponse`: `id`, `full_name`, `email`, `role`, `is_active`, `created_at`.
   * HTTP Status Code: `200 OK` (hoặc `201 Created`).

---

## 2. POST `/auth/login` - Đăng nhập hệ thống

### 🎯 Mục đích:
Xác thực email và mật khẩu của người dùng, cấp cặp Token (`access_token`, `refresh_token`).

### 📥 Đầu vào (Request):
* **Body (JSON):** `UserLogin`
  * `email`: string (bắt buộc)
  * `password`: string (bắt buộc)

### 🔄 Các bước xử lý (Workflow):
1. **Router (`router/auth.py`):** Gọi `authenticate_user(credentials, db)`.
2. **Kiểm tra tài khoản tồn tại:**
   * Truy vấn bảng `users` tìm user có `email` trùng khớp.
   * **Nếu không thấy user:** Bắn lỗi `BadRequestException` (`400 Bad Request`) với message `"Email hoặc mật khẩu không đúng"`.
3. **Xác thực mật khẩu:**
   * So sánh `password` gửi lên với `password_hash` bằng `verify_pass()`.
   * **Nếu mật khẩu sai:** Bắn lỗi `BadRequestException` (`400 Bad Request`) với message `"Email hoặc mật khẩu không đúng"`.
4. **Kiểm tra trạng thái tài khoản:**
   * Kiểm tra `user.is_active`.
   * **Nếu `is_active == False`:** Bắn lỗi `ForbiddenException` (`403 Forbidden`) với message `"Tài khoản đã bị vô hiệu hóa"`.
5. **Tạo JWT Tokens (`core/security.py`):**
   * **Access Token:** Chứa payload (`sub` = email, `user_id`, `type` = `"access"`, `exp` = thời gian hết hạn 30 phút).
   * **Refresh Token:** Chứa payload (`sub` = email, `user_id`, `type` = `"refresh"`, `exp` = thời gian hết hạn 7 ngày).
6. **Trả về kết quả:**
   * Response Model: `Token` (`access_token`, `refresh_token`, `token_type` = `"bearer"`).
   * HTTP Status Code: `200 OK`.

---

## 3. POST `/auth/refresh` - Lấy Access Token mới từ Refresh Token

### 🎯 Mục đích:
Cấp lại cặp Access Token & Refresh Token mới khi Access Token cũ đã hết hạn mà không cần bắt người dùng nhập lại mật khẩu.

### 📥 Đầu vào (Request):
* **Body (JSON):** `RefreshRequest`
  * `refresh_token`: string (bắt buộc)

### 🔄 Các bước xử lý (Workflow):
1. **Giải mã Refresh Token:**
   * Gọi `decode_access_token(refresh_token)`.
   * **Nếu Token bị lỗi/hết hạn/không hợp lệ:** Bắn lỗi `UnauthorizedException` (`401 Unauthorized`).
2. **Kiểm tra loại Token (`type`):**
   * Kiểm tra `payload.get("type") == "refresh"`.
   * **Nếu `type` không phải "refresh":** Bắn lỗi `UnauthorizedException` với message `"Token không đúng loại (yêu cầu refresh token)"`.
3. **Kiểm tra thông tin User trong Token:**
   * Lấy `user_id` và `email` từ token payload.
   * **Nếu thiếu `user_id` hoặc `email`:** Bắn lỗi `UnauthorizedException` (`401 Unauthorized`).
4. **Kiểm tra thông tin User trong Database:**
   * Truy vấn bảng `users` tìm người dùng theo `user_id`.
   * **Nếu user không tồn tại:** Bắn lỗi `UnauthorizedException` với message `"Người dùng không tồn tại"`.
   * **Nếu `user.is_active == False`:** Bắn lỗi `ForbiddenException` (`403 Forbidden`) với message `"Tài khoản đã bị vô hiệu hóa"`.
5. **Cấp Token mới:**
   * Tạo `new_access_token` và `new_refresh_token` mới.
6. **Trả về kết quả:**
   * Response Model: `Token` (`access_token`, `refresh_token`, `token_type` = `"bearer"`).
   * HTTP Status Code: `200 OK`.
