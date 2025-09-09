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
                f"scene_{ url['num_of_image']}": f"{url['output_file']}",
            })
        imagen_data.images_path = url_temp
        imagen_data.status = "done"

        if save:
            S2PModule.write_or_update_data(imagen_data.model_dump(), uuid)
            logging.info(f"[IMAGEN] Initialized image entry for uuid={uuid}, id={request.id}")

    except Exception as e:
        logging.error(f"[IMAGEN ERROR] Exception for uuid={uuid}, id={request.id}: {e}", exc_info=True)
        imagen_data.status = "error"
        if save:
            S2PModule.write_or_update_data(imagen_data.model_dump(), request.id)


def get_image_by_uuid(uuid: str):
    return S2PModule.get_data_by_uuid(uuid)

def get_transcript(request: ImagenRequest, uuid: str) -> str:
    if request.use_script:
        return request.script

    data = T2SModule.get_data_by_uuid(uuid)

    if data and request.id:
        order_url = data.get("content_order") 
        if order_url:
            # Bỏ domain để còn lại đường dẫn tương đối nội bộ
            try:
                order_path_str = re.sub(f"^{SERVER_HOST}", "", order_url, flags=re.IGNORECASE)
                order_path = Path(order_path_str.strip("\\/"))
                if order_path.exists():
                    logging.info(f"[ORDER] Founded Content order: {order_path}")
                    return order_path.read_text(encoding="utf-8")
            except Exception as e:
                raise ValueError(f"Failed to load content_order file: {e}")

        # Nếu không có hoặc sai, fallback về OrderContent/{id}.txt
        default_path = Path("database/OrderContent") / f"{request.id}.txt"
        if default_path.exists():
            return default_path.read_text(encoding="utf-8")

    raise ValueError(f"No transcript found for uuid={uuid}")
