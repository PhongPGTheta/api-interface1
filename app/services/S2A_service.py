import logging
from datetime import datetime
from models.s2amodel import AudioData, AudioRequest
from functions.S2A_process import AudioService, MergeAudio
from database.datacontrol import T2SModule, S2AModule
from core.config import DATA_AUDIO_PATH, SERVER_HOST
from schemas.rules import DataReturn
from pathlib import Path
import re
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)

def process_audio(request: AudioRequest, uuid: str, save: bool = True):
    logging.info(f"[AUDIO] Start processing audio uuid={uuid}, id={request.id}")

    audio_data = AudioData(
        id=request.id,
        uuid=uuid,
        transcript=request.script if request.use_script else "",
        audio_path="",
        status="processing",
        created_at=datetime.now().isoformat()
    )

    if save:
        S2AModule.write_or_update_data(audio_data.model_dump(), request.id)
        logging.info(f"[AUDIO] Initialized audio entry for uuid={uuid}, id={request.id}")

    try:
        transcript = get_transcript(request, uuid)
        audio_path = AudioService.process_audio(transcript, DATA_AUDIO_PATH, id=request.id)
        # audio_dir = f"{DATA_AUDIO_PATH}/{request.id}"
        # audio_path = MergeAudio.merge(audio_dir, [f"{request.id}_part_{i}.wav" for i in range(1, 10)], id=request.id)
        logging.info(f"[AUDIO] Audio created at: {audio_path}")
        if audio_path is None:
            logging.info(f"[AUDIO NOT SUCESS] Can't found Audio data.")
            audio_data.status = "error"
            if save:
                S2AModule.write_or_update_data(audio_data.model_dump(), request.id)
        else:
            DataReturn.server_url(audio_path)
            audio_data.audio_path = str(audio_path)
            audio_data.status = "done"

        S2AModule.write_or_update_data(audio_data.model_dump(), request.id)
        logging.info(f"[AUDIO] Finished and saved entry for uuid={uuid}, id={request.id}")

    except Exception as e:
        logging.error(f"[AUDIO ERROR] Exception for uuid={uuid}, id={request.id}: {e}", exc_info=True)
        audio_data.status = "error"
        if save:
            S2AModule.write_or_update_data(audio_data.model_dump(), request.id)

def get_transcript(request: AudioRequest, uuid: str) -> str:
    logging.info(f"[AUDIO] get_transcript called with use_script={request.use_script}, script={request.script}, uuid={uuid}")
    
    if request.use_script and request.script:
        logging.info(f"[AUDIO] Using provided script: {request.script[:100]}...")
        return request.script

    data = T2SModule.get_data_by_uuid(uuid)
    logging.info(f"[AUDIO] Retrieved T2S data: {data}")

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

def get_audio_by_uuid(uuid: str):
    return S2AModule.get_data_by_uuid(uuid)


