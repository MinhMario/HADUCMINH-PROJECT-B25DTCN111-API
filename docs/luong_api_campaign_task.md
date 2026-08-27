# Luồng xử lý API Campaign Task & Comment (Công việc & Bình luận)

Tài liệu chi tiết luồng xử lý (Workflow/Sequence) cho nhóm API **Campaign Task** và **Task Comment**.

---

## 1. POST `/campaigns/{campaign_id}/campaign-tasks` - Tạo công việc mới trong chiến dịch

### 🎯 Mục đích:
Tạo một công việc (Task) mới gán cho thành viên trong chiến dịch.

### 📥 Đầu vào (Request):
* **Header:** `Authorization: Bearer <access_token>`
* **Body (JSON):** `CampaignTaskCreate`
  * `title`: string (bắt buộc)
  * `description`: string | None
  * `due_date`: datetime | None
  * `status`: string | None (TODO / IN_PROGRESS / DONE, Mặc định TODO)
  * `priority`: string | None (LOW / MEDIUM / HIGH, Mặc định MEDIUM)
  * `assignee_id`: int | None (ID người dùng được giao task)

### 🔄 Các bước xử lý (Workflow):
1. **Kiểm tra Campaign tồn tại:** Lỗi `404 Not Found` nếu chiến dịch không tồn tại/đã bị xóa.
2. **Kiểm tra người tạo task:**
   * Phải là **Owner** hoặc **Member** của chiến dịch này. Nếu không -> Lỗi `403 Forbidden`.
3. **Validate dữ liệu đầu vào:**
   * **Status:** Nếu truyền `status`, phải thuộc tập `{"TODO", "IN_PROGRESS", "DONE"}` (không phân biệt hoa thường). Nếu sai -> Lỗi `400 Bad Request`.
   * **Priority:** Nếu truyền `priority`, phải thuộc tập `{"LOW", "MEDIUM", "HIGH"}`. Nếu sai -> Lỗi `400 Bad Request`.
4. **Validate `assignee_id` (nếu được truyền):**
   * Người được gán task phải là **Owner** hoặc là **Member** thuộc chiến dịch này.
   * **Nếu không thuộc chiến dịch:** Bắn lỗi `BadRequestException` (`400 Bad Request`) với message `"Người được gán không thuộc chiến dịch này"`.
5. **Tạo Task:** Khởi tạo `CampaignTask`, lưu vào CSDL (`db.add`, `db.commit`, `db.refresh`).
6. **Trả về kết quả:** `CampaignTaskResponse`. Status Code: `201 Created`.

---

## 2. GET `/campaigns/{campaign_id}/campaign-tasks` - Danh sách công việc của chiến dịch

### 🎯 Mục đích:
Lấy danh sách công việc thuộc một chiến dịch với tính năng Phân trang, Lọc (`status`, `priority`, `assignee_id`), Tìm kiếm (`search`), Sắp xếp (`sort_by`, `order`).

### 📥 Đầu vào (Request):
* **Query Parameters:** `page`, `size`, `sort_by` (created_at/due_date), `order` (asc/desc), `status`, `priority`, `assignee_id`, `search` (lọc tiêu đề task).

### 🔄 Các bước xử lý (Workflow):
1. **Kiểm tra Campaign & Quyền thành viên:** Lỗi `404` nếu không tìm thấy, Lỗi `403` nếu người truy cập không thuộc chiến dịch.
2. **Xây dựng Query:** `db.query(CampaignTask).filter(CampaignTask.campaign_id == campaign_id)`.
3. **Áp dụng các bộ lọc (Filters):**
   * Lọc theo `status` nếu có.
   * Lọc theo `priority` nếu có.
   * Lọc theo `assignee_id` nếu có.
   * Tìm kiếm tương đối tên công việc: `CampaignTask.title.ilike('%search%')`.
4. **Sắp xếp & Phân trang:** Áp dụng `apply_sorting` và `paginate`.
5. **Trả về kết quả:** `PaginatedResponse[CampaignTaskResponse]`. Status Code: `200 OK`.

---

## 3. GET `/campaign-tasks/{id}` - Xem chi tiết công việc

### 🎯 Mục đích:
Xem thông tin chi tiết của 1 Task theo Task ID.

### 🔄 Các bước xử lý (Workflow):
1. **Truy vấn Task:** Tìm `CampaignTask` theo `id`. Lỗi `404` nếu không tồn tại.
2. **Truy vấn Campaign chứa Task:** Kiểm tra campaign tồn tại & `is_deleted == False`. Lỗi `404` nếu không tìm thấy.
3. **Kiểm tra quyền truy cập:** Người gọi API phải thuộc chiến dịch đó. Lỗi `403` nếu không phải thành viên.
4. **Trả về kết quả:** `CampaignTaskResponse`. Status Code: `200 OK`.

---

## 4. PATCH `/campaign-tasks/{id}` - Cập nhật công việc (Phân quyền theo vai trò)

### 🎯 Mục đích:
Cập nhật nội dung, trạng thái, độ ưu tiên hoặc người thực hiện task.

### 🚨 Quy tắc Phân quyền (Authorization Rules):
* **Owner của Campaign:** Có toàn quyền chỉnh sửa tất cả các trường (`title`, `description`, `status`, `priority`, `due_date`, `assignee_id`).
* **Assignee (Người được gán task):** **Chỉ được phép cập nhật trạng thái (`status`)** của task. Không được sửa tiêu đề, mô tả, hay gán người khác.
* **Người dùng khác:** Không có quyền chỉnh sửa -> Lỗi `403 Forbidden`.

### 🔄 Các bước xử lý (Workflow):
1. **Truy vấn Task & Campaign:** Kiểm tra sự tồn tại (Lỗi `404`).
2. **Xác định vai trò người dùng:**
   * `is_owner = (campaign.owner_id == user_id)`
   * `is_assignee = (task.assignee_id == user_id)`
3. **Kiểm tra quyền truy cập chung:**
   * **Nếu không phải Owner VÀ không phải Assignee:** Bắn lỗi `ForbiddenException` (`403`) với message `"Bạn không có quyền chỉnh sửa task này"`.
4. **Kiểm tra giới hạn với Assignee:**
   * Nếu `is_assignee` (mà không phải Owner) gửi thay đổi các trường ngoài `status`: Bắn lỗi `ForbiddenException` (`403`) với message `"Assignee chỉ có quyền cập nhật trạng thái (status) của task"`.
5. **Validate dữ liệu cập nhật:**
   * Nếu đổi `assignee_id`: Kiểm tra người mới có thuộc chiến dịch không (`400 Bad Request` nếu không thuộc).
   * Nếu đổi `status` / `priority`: Validate các giá trị hợp lệ (`TODO`, `IN_PROGRESS`, `DONE` / `LOW`, `MEDIUM`, `HIGH`).
6. **Lưu thay đổi:** Gán thuộc tính mới, `db.commit()`, `db.refresh()`.
7. **Trả về kết quả:** `CampaignTaskResponse`. Status Code: `200 OK`.

---

## 5. DELETE `/campaign-tasks/{id}` - Xóa công việc

### 🎯 Mục đích:
Xóa vĩnh viễn 1 công việc khỏi hệ thống (Chỉ dành cho **Owner của Campaign**).

### 🔄 Các bước xử lý (Workflow):
1. **Truy vấn Task & Campaign:** Lỗi `404` nếu không tìm thấy.
2. **Kiểm tra quyền xóa:**
   * So sánh `campaign.owner_id != user_id`.
   * **Nếu không phải Owner:** Bắn lỗi `ForbiddenException` (`403`) với message `"Chỉ chủ chiến dịch mới có quyền xóa task"`.
3. **Thực hiện xóa:** `db.delete(task)`, `db.commit()`.
4. **Trả về kết quả:** `{"message": "Xóa task thành công"}`. Status Code: `200 OK`.

---

## 6. POST `/campaign-tasks/{id}/comments` - Thêm bình luận vào công việc

### 🎯 Mục đích:
Thêm một bình luận (Comment) vào task (Dành cho tất cả **Thành viên/Owner** của chiến dịch).

### 📥 Đầu vào (Request):
* **Body (JSON):** `TaskCommentCreate` (`content`: string - bắt buộc)

### 🔄 Các bước xử lý (Workflow):
1. **Truy vấn Task & Campaign:** Lỗi `404` nếu không tồn tại.
2. **Kiểm tra quyền thành viên:** Lỗi `403` nếu người dùng không thuộc chiến dịch chứa task này.
3. **Tạo Comment:**
   * Tạo `TaskComment` với `task_id`, `user_id = current_user.id`, `content = content.strip()`.
   * `db.add()`, `db.commit()`, `db.refresh()`.
4. **Trả về kết quả:** `TaskCommentResponse` (`id`, `task_id`, `user_id`, `content`, `created_at`). Status Code: `201 Created`.

---

## 7. GET `/campaign-tasks/{id}/comments` - Xem danh sách bình luận của công việc

### 🎯 Mục đích:
Xem danh sách các bình luận trong một task (có phân trang và sắp xếp theo thời gian).

### 📥 Đầu vào (Request):
* **Query Parameters:** `page`, `size`, `sort_by` (mặc định created_at), `order` (asc/desc - mặc định asc).

### 🔄 Các bước xử lý (Workflow):
1. **Truy vấn Task & Campaign & Kiểm tra quyền thành viên:** Lỗi `404` nếu không thấy, Lỗi `403` nếu không thuộc chiến dịch.
2. **Truy vấn Bình luận:** Lọc `TaskComment.task_id == id`, sắp xếp theo `created_at` (asc/desc), gọi `paginate`.
3. **Trả về kết quả:** `PaginatedResponse[TaskCommentResponse]`. Status Code: `200 OK`.
