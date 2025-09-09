from models.t2smodel import OrderData, OrderRequest
from core.config import NUMBER_WORDS_OF_CONTENT
from database.datacontrol import T2SModule
from functions.T2S_process import TranscriptManager
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)

def process_order(request: OrderRequest, uuid: str, save: bool = True):
    logging.info(f"[ORDER] Start processing order uuid={uuid}, id={request.id}")
    now = datetime.now().isoformat()
    order_data = OrderData(
        uuid=uuid,
        id=request.id,
        url=request.url,
        content_order=request.order,
        length=request.length or NUMBER_WORDS_OF_CONTENT,
        task=request.task or "Gemini",
        status="processing",
        platform=request.platform,
        language=getattr(request, 'language', 'en'),
        created_at=now
    )
    # logging.info(f"[ORDER] Initial order data created: {order_data}")
    # logging.info(f"[ORDER] : {request.order}")

    T2SModule.write_or_update_data(order_data.model_dump(), request.id)
    logging.info(f"[ORDER] Created empty order data for uuid={uuid}, id={request.id}")
    TranscriptManager.transcript_to_new_script(order_data, uuid)


def get_order_by_uuid(uuid: str):
    return T2SModule.get_data_by_uuid(uuid)

def get_status_by_uuid(uuid: str):
    data = T2SModule.get_data_by_uuid(uuid)
    if data:
        return {"uuid": uuid, "status": data.get("status", "unknown")}
    return {"uuid": uuid, "status": "not found"}


