from pydantic import BaseModel
from typing import Optional, List
from typing import Optional

class OrderRequest(BaseModel):
    url : str # URL của video YouTube
    platform: str = "youtube"
    id: Optional[int] = None # ID của  video được order
    order: Optional[str] = "" # Nội dung order của video
    task: Optional[str] = "Gemini" # Loại task, mặc định là Gemini
    length: Optional[int] = 10000 # Độ dài nội dung order, mặc định là 10000 ký tự

class OrderResponse(BaseModel):
    uuid: str
    status: str

class CreateActionModule(BaseModel):
    uuid: Optional[str] # UUID của order
    url : str # URL của video YouTube
    platform: str = "youtube"
    language: Optional[str] = "en" # Ngôn ngữ của video
    id: Optional[int] = None # ID của  video được order
    order: Optional[str] = "" # Nội dung order của video
    length: Optional[int] = 10000 # Độ dài nội dung order, mặc định là 10000 ký tự
    task: Optional[str] = "Gemini" # Loại task, mặc định là Gemini
    
class APIHeaders(BaseModel):
    accept: str = "application/json"
    accept_language: str = "vi-VN,vi;q=0.9"
    cache_control: str = "no-cache"
    content_type: str = "application/json"
    sec_ch_ua: str = '"Chromium";v="99", "Google Chrome";v="99", "Not.A/Brand";v="99"'
    sec_ch_ua_mobile: str = "?0"
    sec_ch_ua_platform: str = '"Windows"'
    user_agent: str

class OrderData(BaseModel):
    uuid: str
    #id: int
    id: Optional[int] = None
    url: str
    content_order: str = ""
    length: int = 6500  # Độ dài nội dung order, mặc định là 6500 từ ( words)
    task: str = "Gemini"  # Loại task, mặc định là Gemini
    status: str = "processing"
    platform: str = "youtube"
    language: Optional[str] = "en"
    created_at: Optional[str] = None