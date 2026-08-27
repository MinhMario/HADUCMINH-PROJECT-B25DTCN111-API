# Luồng xử lý API Campaign (Chiến dịch & Thành viên)

Tài liệu chi tiết luồng xử lý (Workflow/Sequence) cho nhóm API **Campaign** và **Campaign Member**.

---

## 1. POST `/campaigns/` - Tạo chiến dịch mới

### 🎯 Mục đích:
Tạo một chiến dịch tiếp thị mới. Người tạo chiến dịch tự động trở thành Chủ sở hữu (**OWNER**) và là thành viên đầu tiên của chiến dịch đó.

### 📥 Đầu vào (Request):
* **Header:** `Authorization: Bearer <access_token>`
* **Body (JSON):** `CampaignCreate`
  * `name`: string (bắt buộc)
  * `description`: string | None

### 🔄 Các bước xử lý (Workflow):
1. **Xác thực người dùng:** `get_current_user` kiểm tra token, lấy `owner_id = current_user.id`.
2. **Khởi tạo Campaign:**
   * Tạo bản ghi `Campaign` với `name`, `description`, `owner_id`.
   * Lưu vào CSDL (`db.add`, `db.commit`, `db.refresh`).
3. **Tự động thêm Owner vào bảng `campaign_members`:**
   * Tạo bản ghi `CampaignMember` với `campaign_id = new_campaign.id`, `user_id = owner_id`, `role = "OWNER"`.
   * Lưu vào CSDL (`db.add`, `db.commit`).
4. **Trả về kết quả:** `CampaignResponse` (`id`, `name`, `description`, `owner_id`, `created_at`). Status Code: `201 Created`.

---

## 2. GET `/campaigns/` - Lấy danh sách chiến dịch của tôi

### 🎯 Mục đích:
Lấy danh sách phân trang các chiến dịch mà người dùng đăng nhập là **Chủ sở hữu (Owner)** hoặc **Thành viên (Member)**.

### 📥 Đầu vào (Request):
* **Header:** `Authorization: Bearer <access_token>`
* **Query Parameters:** `page`, `size`, `search` (lọc theo tên campaign, mặc định sắp xếp theo created_at desc).

### 🔄 Các bước xử lý (Workflow):
1. **Lấy danh sách ID campaign người dùng tham gia:**
   * Truy vấn bảng `campaign_members` lọc `user_id == current_user.id` thu được `member_campaign_ids`.
2. **Lọc Campaign hợp lệ:**
   * Lọc những campaign có `is_deleted == False` VÀ (`owner_id == user_id` HOẶC `id` nằm trong `member_campaign_ids`).
3. **Tìm kiếm & Sắp xếp & Phân trang:**
   * Áp dụng tìm kiếm tương đối theo tên (`Campaign.name.ilike(...)`).
   * Sắp xếp theo cột yêu cầu và phân trang (`paginate`).
4. **Trả về kết quả:** `PaginatedResponse[CampaignResponse]`. Status Code: `200 OK`.

---

## 3. GET `/campaigns/{campaign_id}` - Xem chi tiết chiến dịch

### 🎯 Mục đích:
Xem thông tin chi tiết một chiến dịch cụ thể theo ID.

### 🔄 Các bước xử lý (Workflow):
1. **Truy vấn Campaign:**
   * Tìm trong CSDL theo `campaign_id` và `is_deleted == False`.
   * **Nếu không thấy:** Bắn lỗi `NotFoundException` (`404 Not Found`).
2. **Kiểm tra quyền truy cập:**
   * Kiểm tra người dùng có trong bảng `campaign_members` của campaign này hay không.
   * **Nếu không phải thành viên:** Bắn lỗi `ForbiddenException` (`403 Forbidden`) với message `"Bạn không phải thành viên của campaign này"`.
3. **Trả về kết quả:** `CampaignResponse`. Status Code: `200 OK`.

---

## 4. PUT & PATCH `/campaigns/{campaign_id}` - Cập nhật chiến dịch

### 🎯 Mục đích:
Chỉnh sửa tên hoặc mô tả của chiến dịch (Chỉ dành cho **OWNER**).

### 🔄 Các bước xử lý (Workflow):
1. **Truy vấn Campaign:** Kiểm tra sự tồn tại và `is_deleted == False`. Lỗi `404` nếu không tìm thấy.
2. **Kiểm tra quyền OWNER:**
   * So sánh `campaign.owner_id != current_user.id`.
   * **Nếu không phải Owner:** Bắn lỗi `ForbiddenException` (`403 Forbidden`) với message `"Bạn không phải chủ của campaign này"`.
3. **Cập nhật dữ liệu:**
   * Lấy dữ liệu gửi lên (`exclude_unset=True` với PATCH hoặc toàn bộ với PUT).
   * Gán giá trị mới vào object `campaign`, `db.commit()` và `db.refresh()`.
4. **Trả về kết quả:** `CampaignResponse`. Status Code: `200 OK`.

---

## 5. DELETE `/campaigns/{campaign_id}` - Xóa chiến dịch (Soft Delete)

### 🎯 Mục đích:
Xóa mềm một chiến dịch ra khỏi hệ thống (Chỉ dành cho **OWNER**).

### 🔄 Các bước xử lý (Workflow):
1. **Truy vấn Campaign:** Kiểm tra sự tồn tại và `is_deleted == False`. Lỗi `404` nếu không tìm thấy.
2. **Kiểm tra quyền OWNER:**
   * So sánh `campaign.owner_id != current_user.id`.
   * **Nếu không phải Owner:** Bắn lỗi `ForbiddenException` (`403 Forbidden`).
3. **Thực hiện Xóa mềm (Soft Delete):**
   * Đặt `campaign.is_deleted = True`.
   * Đặt `campaign.deleted_at = datetime.utcnow()`.
   * Lưu thay đổi vào CSDL (`db.commit()`).
4. **Trả về kết quả:** Trả về đối tượng `CampaignResponse`. Status Code: `200 OK`.

---

## 6. POST `/campaigns/{campaign_id}/members` - Thêm thành viên vào chiến dịch

### 🎯 Mục đích:
Chủ sở hữu (**OWNER**) thêm một người dùng khác vào chiến dịch.

### 📥 Đầu vào (Request):
* **Body (JSON):** `CampaignMemberAdd` (`user_id`: int)

### 🔄 Các bước xử lý (Workflow):
1. **Kiểm tra Campaign tồn tại & kiểm tra quyền OWNER:**
   * Lỗi `404` nếu Campaign không tồn tại/đã bị xóa.
   * Lỗi `403` nếu người thực hiện không phải Owner của chiến dịch.
2. **Kiểm tra User được thêm:**
   * Truy vấn bảng `users` tìm người dùng có `id == new_user_id`.
   * **Nếu không tồn tại:** Bắn lỗi `NotFoundException` (`404 Not Found`) với message `"User không tồn tại"`.
3. **Kiểm tra người dùng đã tham gia chưa:**
   * Truy vấn bảng `campaign_members` kiểm tra cặp `(campaign_id, new_user_id)`.
   * **Nếu đã tồn tại:** Bắn lỗi `BadRequestException` (`400 Bad Request`) với message `"User đã là thành viên của campaign này"`.
4. **Thêm thành viên:**
   * Tạo `CampaignMember` mới với `role = "MEMBER"`.
   * `db.add()`, `db.commit()`, `db.refresh()`.
5. **Trả về kết quả:** `CampaignMemberResponse`. Status Code: `201 Created`.

---

## 7. GET `/campaigns/{campaign_id}/members` - Xem danh sách thành viên

### 🎯 Mục đích:
Xem danh sách tất cả các thành viên trong chiến dịch (Dành cho bất kỳ **Thành viên/Owner** nào của chiến dịch).

### 🔄 Các bước xử lý (Workflow):
1. **Kiểm tra Campaign tồn tại:** Lỗi `404` nếu không tìm thấy.
2. **Kiểm tra tư cách thành viên:**
   * Lỗi `403` nếu người gọi API không thuộc campaign này.
3. **Truy vấn danh sách:**
   * Trả về toàn bộ danh sách `CampaignMember` trong campaign.
4. **Trả về kết quả:** `list[CampaignMemberResponse]`. Status Code: `200 OK`.

---

## 8. DELETE `/campaigns/{campaign_id}/members/{user_id}` - Xóa thành viên khỏi chiến dịch

### 🎯 Mục đích:
Chủ sở hữu (**OWNER**) xóa một thành viên ra khỏi chiến dịch.

### 🔄 Các bước xử lý (Workflow):
1. **Kiểm tra Campaign tồn tại & kiểm tra quyền OWNER:** Lỗi `404` nếu không tìm thấy, Lỗi `403` nếu không phải Owner.
2. **Kiểm tra thành viên cần xóa:**
   * Truy vấn `campaign_members` tìm cặp `(campaign_id, user_id)`.
   * **Nếu không tồn tại:** Bắn lỗi `NotFoundException` (`404`) với message `"Thành viên không tồn tại trong campaign này"`.
3. **Kiểm tra không cho phép xóa Owner:**
   * So sánh `user_id == campaign.owner_id`.
   * **Nếu trùng:** Bắn lỗi `BadRequestException` (`400`) với message `"Không thể xóa owner của campaign"`.
4. **Thực hiện xóa:**
   * `db.delete(member)`, `db.commit()`.
5. **Trả về kết quả:** Status Code: `204 No Content`.
