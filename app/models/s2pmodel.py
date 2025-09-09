from pydantic import BaseModel
from typing import Optional, List, Union, Dict
from typing import Optional


class ImagenRequest(BaseModel):
    id: Optional[int] = None  # ID của video được order
    uuid: Optional[str] = None  # UUID của order, nếu có
    script: Optional[str] = None  # Kịch bản đã được tạo từ trước, nếu có
    use_script: Optional[bool] = False  # Sử dụng kịch bản đã có hay không

class ImagenResponse(BaseModel):
    uuid: str
    status: str

class ImagenData(BaseModel):
    #id: int
    id: Optional[int] = None
    uuid: str
    script: str = ""
    status: str = "processing"
    images_path: List[Dict] = ""
    created_at: Optional[str] = None