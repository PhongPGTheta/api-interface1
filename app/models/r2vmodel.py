from pydantic import BaseModel
from typing import Optional, List
from typing import Optional


class RenderRequest(BaseModel):
    id: Optional[int] = None  # ID của video được order
    uuid: Optional[str] = None  # UUID của order, nếu có
    url_images: Optional[List[str]] = None  # Danh sách URL hình ảnh
    url_audio: Optional[str] = None  # URL của file âm thanh

class RenderResponse(BaseModel):
    uuid: str
    status: str
    video_path: Optional[str] = None  # Đường dẫn đến video đã render, nếu có
    error: Optional[str] = None  # Thông báo lỗi nếu có

class RenderData(BaseModel):
    #id: int
    id: Optional[int] = None
    uuid: str
    url_images: Optional[str] = None
    url_audio: Optional[str] = None
    status: str = "processing"
    video_path: Optional[str] = None
    created_at: Optional[str] = None  # Thời gian tạo order, có thể để trống nếu không cần thiết