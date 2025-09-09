from database.datacontrol import R2VModule, S2AModule, S2PModule
from models.r2vmodel import RenderRequest, RenderData
from schemas.rules import DataReturn
from core.config import DATA_AUDIO_PATH, DATA_IMAGEN_PATH
from functions.R2V_process import VideoManager
from pathlib import Path
from datetime import datetime
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)

def process_video(request: RenderRequest, uuid: str, save: bool = True):
    logging.info(f"[RENDER] Start processing audio uuid={uuid}, id={request.id}")

    render_data = RenderData(
        id=request.id,
        uuid=uuid,
        url_images= "",
        url_audio= "",
        status = "processing",
        video_path= "",
        created_at = datetime.now().isoformat()
    )
    
    if save:
        R2VModule.write_or_update_data(render_data.model_dump(), request.id)
        logging.info(f"[RENDER] Initialized render entry for uuid={uuid}, id={request.id}")

    try:
        # Try to find actual audio/image paths by UUID first
        audio_data = S2AModule.get_data_by_uuid(uuid)
        imagen_data = S2PModule.get_data_by_uuid(uuid)
        
        if audio_data and 'audio_path' in audio_data:
            # Extract ID from audio path: /database/Audio/ID/file.wav -> ID
            audio_path_str = audio_data['audio_path']
            if '/Audio/' in audio_path_str:
                actual_audio_id = audio_path_str.split('/Audio/')[1].split('/')[0]
                audio_path = get_audio_path(actual_audio_id)
            else:
                audio_path = get_audio_path(request.id)
        else:
            audio_path = get_audio_path(request.id)
            
        if imagen_data and 'images_path' in imagen_data and imagen_data['images_path']:
            # Try to extract ID from first image path
            first_image = imagen_data['images_path'][0]
            if isinstance(first_image, dict) and 'path' in first_image:
                image_path_str = first_image['path']
                if '/Imagen/' in image_path_str:
                    actual_image_id = image_path_str.split('/Imagen/')[1].split('/')[0]
                    imagen_path = get_imagen_path(actual_image_id)
                else:
                    imagen_path = get_imagen_path(request.id)
            else:
                imagen_path = get_imagen_path(request.id)
        else:
            imagen_path = get_imagen_path(request.id)
            
        video_path = VideoManager.process_video(imagen_path, audio_path, id=request.id, uuid=uuid)
        logging.info(f"[RENDER] Render created at: {video_path}")

        render_data.url_images = imagen_path
        render_data.url_audio = audio_path
        video_url = DataReturn.server_url(str(video_path))
        render_data.video_path = str(video_url)
        render_data.status = "done"

        R2VModule.write_or_update_data(render_data.model_dump(), request.id)
        logging.info(f"[RENDER] Finished and saved entry for uuid={uuid}, id={request.id}")

    except Exception as e:
        logging.error(f"[RENDER ERROR] Exception for uuid={uuid}, id={request.id}: {e}", exc_info=True)
        render_data.status = "error"
        if save:
            R2VModule.write_or_update_data(render_data.model_dump(), request.id)



def get_video_by_uuid(uuid: str):
    return R2VModule.get_data_by_uuid(uuid)

def get_imagen_path(id: int):
    return f"{DATA_IMAGEN_PATH}/{id}"
def get_audio_path(id: int):
    return f"{DATA_AUDIO_PATH}/{id}"
