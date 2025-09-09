from database.datacontrol import S2PModule, T2SModule
from models.s2pmodel import ImagenRequest, ImagenData
from functions.S2P_process import ImagenManager
from schemas.rules import DataReturn
from core.config import SERVER_HOST
from pathlib import Path
import logging
import time
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)


def process_image( request: ImagenRequest, uuid: str , save: bool = True):
    logging.info(f"[IMAGEN] Starting image generation process for ID : {request.id}, UUID: {uuid}")
    
    imagen_data = ImagenData(
        id=request.id,
        uuid=uuid,
        script=request.script if request.use_script else "",
        status="processing",
        images_path=[],
        created_at=datetime.now().isoformat()
    )

    try:
        transcript = get_transcript(request, uuid)
        iurl = ImagenManager.process_imagen(transcript, request.id)
        url_temp = []
        for url in iurl:
            url_temp.append({
                "scene_number": url['num_of_image'],
                "path": url['output_file'],
                "url": url['output_file']
            })
        imagen_data.images_path = url_temp
        imagen_data.status = "done"

        if save:
            S2PModule.write_or_update_data(imagen_data.model_dump(), request.id)
            logging.info(f"[IMAGEN] Initialized image entry for uuid={uuid}, id={request.id}")

    except Exception as e:
        logging.error(f"[IMAGEN ERROR] Exception for uuid={uuid}, id={request.id}: {e}", exc_info=True)
        imagen_data.status = "error"
        if save:
            S2PModule.write_or_update_data(imagen_data.model_dump(), request.id)


def get_image_by_uuid(uuid: str):
    return S2PModule.get_data_by_uuid(uuid)

def get_transcript(request: ImagenRequest, uuid: str) -> str:
    logging.info(f"[IMAGEN] get_transcript called with use_script={request.use_script}, script={request.script}, uuid={uuid}")
    
    if request.use_script and request.script:
        logging.info(f"[IMAGEN] Using provided script: {request.script[:100]}...")
        return request.script

    data = T2SModule.get_data_by_uuid(uuid)
    logging.info(f"[IMAGEN] Retrieved T2S data: {data}")

    if data:
        # Kiểm tra xem order đã hoàn thành chưa
        if data.get("status") != "done":
            raise ValueError(f"Order is still processing (status: {data.get('status')}). Please wait for order to complete.")

        # Thử lấy từ content_order URL trước
        order_url = data.get("content_order") 
        if order_url:
            try:
                # Kiểm tra xem có phải là URL không
                if order_url.startswith("http"):
                    # Bỏ domain để còn lại đường dẫn tương đối nội bộ
                    order_path_str = re.sub(f"^{SERVER_HOST}", "", order_url, flags=re.IGNORECASE)
                    order_path = Path(order_path_str.strip("\\/"))
                    if order_path.exists():
                        logging.info(f"[ORDER] Found Content order file: {order_path}")
                        content = order_path.read_text(encoding="utf-8")
                        logging.info(f"[ORDER] Content loaded from file, length: {len(content)} characters")
                        return content
                else:
                    # Nếu content_order là text trực tiếp (chưa được xử lý)
                    logging.info(f"[ORDER] Using content_order text directly: {order_url[:100]}...")
                    return order_url
            except Exception as e:
                logging.warning(f"[ORDER] Failed to load content_order: {e}")

        # Fallback: thử lấy từ OrderContent/{id}.txt
        if request.id:
            default_path = Path("database/OrderContent") / f"{request.id}.txt"
            if default_path.exists():
                logging.info(f"[ORDER] Found default content: {default_path}")
                content = default_path.read_text(encoding="utf-8")
                logging.info(f"[ORDER] Default content loaded, length: {len(content)} characters")
                return content
        
        # Fallback: thử lấy từ uuid
        uuid_path = Path("database/OrderContent") / f"{uuid}.txt"
        if uuid_path.exists():
            logging.info(f"[ORDER] Found uuid content: {uuid_path}")
            content = uuid_path.read_text(encoding="utf-8")
            logging.info(f"[ORDER] UUID content loaded, length: {len(content)} characters")
            return content

    raise ValueError(f"No transcript found for uuid={uuid}. Data: {data}")
