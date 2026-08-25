from typing import Generic, TypeVar, List
from pydantic import BaseModel

# đại diện cho một kiểu dữ liệu cụ thể
T = TypeVar("T")

# generic cho class sử dụng biến kiểu đó
class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    total_pages: int
    items: List[T]
