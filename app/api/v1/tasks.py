from fastapi import FastAPI, APIRouter, Query, BackgroundTasks, Depends, Header
from models.t2smodel import APIHeaders, OrderRequest, OrderResponse
from models.s2amodel import AudioRequest, AudioResponse
from models.s2pmodel import ImagenRequest, ImagenResponse
from models.r2vmodel import RenderRequest, RenderResponse
from typing import Optional
from user_agents import parse
from schemas.uuid_generated import generate_id
from services.T2S_service import process_order, get_order_by_uuid
from services.S2A_service import process_audio, get_audio_by_uuid
from services.S2P_service import process_image, get_image_by_uuid
from services.R2V_service import process_video, get_video_by_uuid
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/v1/tasks", tags=["Tasks"])

def get_browser_versions(user_agent: str) -> str:
    """Extract Chrome và Chromium versions từ User-Agent"""
    ua = parse(user_agent)
    browser_version = ua.browser.version[0] if ua.browser.version else "0"
    return f'"Chromium";v="{browser_version}", "Google Chrome";v="{browser_version}", "Not.A/Brand";v="99"'

async def validate_headers(
    accept: str = Header(default="application/json"),
    accept_language: str = Header(default="vi-VN,vi;q=0.9"),
    cache_control: str = Header(default="no-cache"),
    content_type: str = Header(default="application/json"),
    user_agent: str = Header(...)
) -> APIHeaders:
    # Lấy version động từ User-Agent
    sec_ch_ua = get_browser_versions(user_agent)
    
    return APIHeaders(
        accept=accept,
        accept_language=accept_language,
        cache_control=cache_control,
        content_type=content_type,
        sec_ch_ua=sec_ch_ua,
        sec_ch_ua_mobile="?0",
        sec_ch_ua_platform='"Windows"',
        user_agent=user_agent
    )

@router.get("/detail")
def check_task():
    return {"message": "Hello why are you here? Welcome to the TheTa Universe API endpoint!"}


@router.post("/create", response_model=OrderResponse)
async def create_work(background_tasks: BackgroundTasks,    
                      request: OrderRequest,
                      headers: APIHeaders = Depends(validate_headers),
                      save: Optional[bool] = Query(default=True)):
    uuid = generate_id()
    # Tạo data rỗng và trả về uuid ngay lập tức
    background_tasks.add_task(process_order, request, uuid, save)
    return OrderResponse(uuid=uuid, status="processing")

@router.get("/create/get")
def get_order(uuid: str):
    data = get_order_by_uuid(uuid)
    if data:
        return {"uuid": uuid,
                "status": data.get("status"),
                "content_order": data.get("content_order")}
    return {"error": "Not found"}

@router.post("/audio", response_model=AudioResponse)
async def create_audio(
    background_tasks: BackgroundTasks,
    request: AudioRequest,
    headers: APIHeaders = Depends(validate_headers),
    save: Optional[bool] = Query(default=True)
):
    if request.uuid is None:
        uuid = generate_id()
    else:
        uuid = request.uuid
    background_tasks.add_task(process_audio, request, uuid, save)
    return AudioResponse(uuid=uuid, status="processing")

@router.get("/audio/get")
def get_audio(uuid: str):
    data = get_audio_by_uuid(uuid)
    if data:
        return {"uuid": uuid,
                "status":data.get("status"),
                "audio_path": data.get("audio_path")}
    return {"error": "Not found"}

@router.post("/imagen", response_model=ImagenResponse)
async def create_images(
    background_tasks: BackgroundTasks,
    request: ImagenRequest,
    headers: APIHeaders = Depends(validate_headers),
    save: Optional[bool] = Query(default=True)
    ):
    if request.uuid is None:
        uuid = generate_id()
    else:
        uuid = request.uuid
    background_tasks.add_task(process_image, request, uuid, save)
    return ImagenResponse(uuid=uuid, status="processing")

@router.get('/imagen/get')
def get_imagen(uuid: str):
    data = get_image_by_uuid(uuid)
    if data:
        return{
            "uuid": uuid,
            "status": data.get("status"),
            "images_path": data.get("images_path")}
    return {"error": "Not found"}

@router.post("/video", response_model=RenderResponse)
async def render_video(
    background_tasks: BackgroundTasks,
    request: RenderRequest,
    headers: APIHeaders = Depends(validate_headers),
    save: Optional[bool] = Query(default=True)
):
    if request.uuid is None:
        uuid = generate_id()
    else:
        uuid = request.uuid
    background_tasks.add_task(process_video, request, uuid, save)
    return RenderResponse(uuid=uuid, status="rendering started")

@router.get("/video/get")
def get_video(uuid: str):
    data = get_video_by_uuid(uuid)
    if data:
        return {
            "uuid": uuid,
            "status": data.get("status"),
            "video_path": data.get("video_path")
        }
    return {"error": "Not found"}