from pydantic import BaseModel
from typing import Optional, List
from typing import Optional

class AudioRequest(BaseModel):
    id: Optional[int] = None  # ID của video được order
    uuid: Optional[str] = None  # UUID của order, nếu có
    script: Optional[str] = None  # Kịch bản đã được tạo từ trước, nếu có
    use_script: Optional[bool] = False  # Sử dụng kịch bản đã có hay không
 
class AudioResponse(BaseModel):
    uuid: str
    status: str

class AudioData(BaseModel):
    #id: int
    id: Optional[int] = None
    uuid: str
    script: str = ""
    status: str = "processing"
    audio_path: str = ""
    created_at: Optional[str] = None