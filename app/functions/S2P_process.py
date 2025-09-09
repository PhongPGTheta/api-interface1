# Import hệ thống và thư viện chuẩn
import os
import sys
import time
import json
import base64
import logging
from pathlib import Path
from datetime import datetime
from io import BytesIO
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
# Import thư viện bên thứ ba
from PIL import Image
import requests
import google.generativeai as gggenai
from google import genai
from google.genai import types

# Import nội bộ từ core
from schemas.rules import DataReturn
from core.config import (
    GOOGLE_API_KEY,
    GOOGLE_API_KEY_IMAGEN,
    IMAGENPROMPT_PATH,
    DATA_IMAGEN_PATH,
    LEONARDO_API_KEY,
    GPT_API_KEY,
    DATA_TEMP,
    SERVER_HOST
)
from core.promptcontrol import PROMPTANALYSIS



logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)

class PromptManager:
    @staticmethod
    def _format_prompt_imagen(scene: dict) -> tuple:

        num = str(scene.get("scene_number", "")).strip()
        desc = str(scene.get("description", "")).strip()
        scene_type = str(scene.get("scene_type", "")).strip()
        location_time = str(scene.get("location_time", "")).strip()
        visual_style = str(scene.get("visual_style", "")).strip()
        color_palette = str(scene.get("color_palette", "")).strip()
        emotion = str(scene.get("dominant_emotion", "")).strip()

        # Prompt mới theo hướng nghệ thuật thời trung cổ và woodcut
        prompt = (
            f"{scene_type.capitalize()} of {desc}.\n"
            f"Setting: {location_time}.\n"
            f"The moment feels {emotion.lower()}, grounded in historical texture and atmosphere.\n"
            f"Depict the scene using the visual style: {visual_style}, with woodcut-style linework and a hand-drawn, medieval illustration feel.\n"
            f"Use a richly textured, high-contrast palette: {color_palette}.\n"
            f"Include period-accurate architecture, terrain, clothing, and objects. Let the light and shadow express the emotional tone.\n"
            f"Avoid modern realism. The scene should feel ancient, symbolic, and mythic.\n"
            f"Aspect ratio: 16:9. Frame all characters clearly. Do not include text, captions, or overlays."
        )
        logging.info(f"[IMAGEN PROMPT] Created optimized prompt for Scene: {num}")
        return num, prompt
    class _gemini_process():
        @staticmethod
        def _analysis(transcript, id: int):
            try:
                gggenai.configure(api_key=GOOGLE_API_KEY)
                model = gggenai.GenerativeModel("gemini-2.0-flash")
                logging.info(f"[GEMINI] Sending request to Gemini API...")

                # Tạo prompt
                words = transcript.split()
                num_scenes = len(words) // 200
                logging.info(f"[GEMINI] Estimated number of scenes: {num_scenes}")
                prompt = PROMPTANALYSIS.replace("[Transcript]", transcript).replace("[Number_of_scenes]", str(num_scenes))
                with open(f"{DATA_TEMP}/imagen_prompt.txt", "a", encoding="utf-8") as f:
                    f.write(prompt)
                # Gửi tới Gemini
                response = model.generate_content(prompt)
                if not response.candidates:
                    logging.error(f"[GEMINI] Blocked prompt. Feedback: {response.prompt_feedback.block_reason}")
                    return None
                content = response.text if hasattr(response, 'text') else str(response)

                # Xử lý lấy JSON
                try:
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                    elif "```" in content:
                        content = content.split("```")[1].strip()

                    scenes = json.loads(content)
                except json.JSONDecodeError as e:
                    logging.error(f"[GEMINI] JSON decode error: {e}")
                    raise ValueError("Invalid JSON response from Gemini")

                # Tạo thư mục nếu chưa có
                os.makedirs(IMAGENPROMPT_PATH, exist_ok=True)

                time = datetime.now()
                # Tạo file path và ghi file
                output_file = os.path.join(IMAGENPROMPT_PATH, f"{time.month}_{time.year}_{id}.json")
                with open(output_file, "w", encoding="utf-8") as f:
                    json.dump(scenes, f, indent=2, ensure_ascii=False)

                logging.info(f"[GEMINI] Scene analysis saved to: {output_file}")
                return output_file

            except Exception as e:
                logging.error(f"[GEMINI] Analysis failed: {e}")
                return None

        @staticmethod
        def _get_imagen_prompt(output_json_scene):
            prompt_list = []
            if not output_json_scene or not os.path.exists(output_json_scene):
                logging.error(f"[IMAGEN ERROR] Scene prompt file not found: {output_json_scene}")
                return []
            with open (f'{output_json_scene}',"r",encoding='utf-8') as f:
                scenes = json.load(f)
                for scene in scenes: 
                    i_num, i_prompt = PromptManager._format_prompt_imagen(scene)
                    prompt_list.append({
                        "num_of_image": int(i_num),
                        "prompt_use" : i_prompt
                    })

            return prompt_list

    @staticmethod
    def transcript_analysis(transcript: str, id: int):
        json_scenes = PromptManager._gemini_process._analysis(transcript, id=id)
        prompt_list = PromptManager._gemini_process._get_imagen_prompt(json_scenes)
        logging.info(f"[IMAGEN PROMPT] Generated prompts Done, total {len(prompt_list)} scenes.")
        # for scene in prompt_list:
        #     logging.info(f"[IMAGEN PROMPT] Scene [{scene['num_of_image']}] - {scene['prompt_use']:[10]}")
        return prompt_list


class ImagenManager:
    @staticmethod
    def GGAIStudio_imagen(prompt: str, id, scene_number: int):
        time.sleep(10)  # Để tránh quá tải API
        try:
            # 1. Khởi tạo client với API key
            client = genai.Client(api_key=GOOGLE_API_KEY_IMAGEN)


            # 2. Gọi API để tạo nội dung có hình ảnh
            response = client.models.generate_content(
                model="gemini-2.0-flash-preview-image-generation",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['TEXT', 'IMAGE']
                )
            )

            # 3. Kiểm tra phản hồi có image
            if not response.candidates:
                logging.error(f"[IMAGEN ERROR] No candidates returned for scene {scene_number}")
                return None, None

            # 4. Duyệt các phần kết quả
            parts = response.candidates[0].content.parts
            for part in parts:
                if part.inline_data is not None:
                    image_data = part.inline_data.data
                    image = Image.open(BytesIO(image_data))

                    # 6. Tạo folder và lưu file ảnh
                    folder = os.path.join(DATA_IMAGEN_PATH, str(id))
                    os.makedirs(folder, exist_ok=True)
                    file_path = os.path.join(folder, f"{id}_scene_{scene_number}_gemini.png")
                    image.save(file_path)
                    file_path = DataReturn.server_url(Path(file_path))
                    logging.info(f"[IMAGEN] Scene {scene_number} saved to: {file_path}")
                    return file_path, file_path

            logging.error(f"[IMAGEN ERROR] No inline_data found for scene {scene_number}")
            return None, None

        except Exception as e:
            logging.error(f"[IMAGEN ERROR] Gemini request failed for scene {scene_number}: {e}")
            return None, None

    @staticmethod
    def GPT_imagen_1(prompt: str, id, scene_number: int,\
                      n: int = 1, size: str = "1377x768"):
        imagen_path = f"{DATA_IMAGEN_PATH}/{id}/{id}_scene_{scene_number}_gpt.jpg"
        url = "https://api.openai.com/v1/images/generations"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GPT_API_KEY}"
        }
        payload = {
            "model": "gpt-image-1",
            "prompt": prompt,
            "n": n,
            "size": size,
            "response_format": "b64_json"  # <- yêu cầu ảnh dạng base64
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                b64_data = data["data"][0]["b64_json"]

                # Giải mã và lưu ảnh
                image_data = base64.b64decode(b64_data)
                imagen_path = Path(imagen_path)
                imagen_path.parent.mkdir(parents=True, exist_ok=True)
                with open(imagen_path, "wb") as f:
                    f.write(image_data)
                imagen_path = DataReturn.server_url(Path(imagen_path))
                logging.info(f"[GPT-IMAGE] Image saved to {imagen_path}")
                return str(imagen_path), str(imagen_path)
            else:
                logging.error(f"[GPT-IMAGE] API request failed: {response.status_code} - {response.text}")
                return None ,None
        except Exception as e:
            logging.error(f"[GPT-IMAGE] Error: {e}")
            return None, None

    @staticmethod
    def LeonardoAPI(num_of_images: int = 1, imagen_prompt: str = "",\
                     height: int = 768, width: int = 1376,\
                     modelId: str = ""):
        url = "https://cloud.leonardo.ai/api/rest/v1/generations"
        payload = {
            "modelId": modelId,
            "num_images": num_of_images,
            "presetStyle": "DYNAMIC",
            "prompt": imagen_prompt,
            "height": height,
            "width": width,
            "enhancePrompt": True
        }
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {LEONARDO_API_KEY}"
        }
        time.sleep(10)  # Để tránh quá tải API
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            logging.info(f"[LEONARDO] API request successful: {data}")
            genid = data['sdGenerationJob']['generationId']
            logging.info(f"[LEONARDO] Generation ID: {genid}")
            return genid
        else:
            logging.error(f"[LEONARDO] API request failed: {response.status_code} - {response.text}")
            return None

    @staticmethod
    def get_models_info(name_model: str = ""):
        IMAGENTEMP_PATH = "database/Temp"
        os.makedirs(IMAGENTEMP_PATH, exist_ok=True)
        url = "https://cloud.leonardo.ai/api/rest/v1/platformModels"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {LEONARDO_API_KEY}"
        }
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            models_data = response.json()
            
            with open(f"{IMAGENTEMP_PATH}/leonardo_models.json", "w", encoding="utf-8") as d:
                json.dump(models_data, d, indent=2, ensure_ascii=False)

            found = False  # cờ đánh dấu nếu tìm được

            # Kiểm tra cấu trúc response
            if isinstance(models_data, dict):
                # Nếu response là dict, tìm key chứa danh sách models
                for key, value in models_data.items():
                    if isinstance(value, list):
                        logging.info(f"[LEONARDO] Processing models from key: {key}")
                        for model in value:
                            if isinstance(model, dict):
                                model_id = model.get("id", "")
                                model_name = model.get("name", "")

                                if not name_model.strip():
                                    # Không nhập model → in danh sách ra thôi
                                    logging.info(f"[LEONARDO] Model: {model_id} - {model_name}")
                                elif model_name.strip().lower() == name_model.strip().lower():
                                    logging.info(f"[LEONARDO] Found model: {model_name} → ID: {model_id}")
                                    found = True
                                    return model_id
            elif isinstance(models_data, list):
                # Nếu response là list trực tiếp
                logging.info(f"[LEONARDO] Processing models from list")
                for model in models_data:
                    if isinstance(model, dict):
                        model_id = model.get("id", "")
                        model_name = model.get("name", "")

                        if not name_model.strip():
                            # Không nhập model → in danh sách ra thôi
                            logging.info(f"[LEONARDO] Model: {model_id} - {model_name}")
                        elif model_name.strip().lower() == name_model.strip().lower():
                            logging.info(f"[LEONARDO] Found model: {model_name} → ID: {model_id}")
                            found = True
                            return model_id

            # Sau vòng lặp:
            if name_model.strip() and not found:
                logging.warning(f"[LEONARDO] Model '{name_model}' not found. Using default.")
                return "b24e16ff-06e3-43eb-8d33-4416c2d75876"
            elif not name_model.strip():
                logging.info(f"[LEONARDO] No specific model requested, using default.")
                return "b24e16ff-06e3-43eb-8d33-4416c2d75876"
                
        except Exception as e:
            logging.error(f"[LEONARDO] Error fetching models: {e}")
            logging.warning(f"[LEONARDO] Using default model due to error.")
            return "b24e16ff-06e3-43eb-8d33-4416c2d75876"
                
    @staticmethod
    def get_imagen(genid: str, id: int, scene_number: int):
        url = f"https://cloud.leonardo.ai/api/rest/v1/generations/{genid}"
        headers = {
            "accept": "application/json",
            "authorization": f"Bearer {LEONARDO_API_KEY}"
        }

        max_retries = 15
        delay_seconds = 10

        for attempt in range(max_retries):
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                images = data.get("generations_by_pk", {}).get("generated_images", [])
                if images:
                    url_imagen = images[0].get("url")
                    if url_imagen:
                        output_file = f"{DATA_IMAGEN_PATH}/{id}/{id}_scene_{scene_number}_leonardo.jpg"
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                        img_data = requests.get(url_imagen).content
                        with open(output_file, "wb") as f:
                            f.write(img_data)
                        output_file = DataReturn.server_url(Path(output_file))
                        logging.info(f"[LEONARDO] Scene {scene_number} saved: {output_file}")
                        return output_file, url_imagen

                logging.info(f"[LEONARDO] Waiting for image ...")
                time.sleep(delay_seconds)
            else:
                logging.error(f"[LEONARDO] Failed to get image info: {response.status_code} - {response.text}")
                break

        logging.warning(f"[LEONARDO] No images found for Scene {scene_number} after {max_retries} attempts.")
        return None, None
        

    @staticmethod
    def process_imagen(transcript: str, id: int):
        is_leonardo = False  # Tạm thời tắt Leonardo do API key lỗi
        is_gpt = False
        is_gemini = True  # Sử dụng Gemini thay thế
        prompt_list = PromptManager.transcript_analysis(transcript, id)
        out_list = []
        
        if is_leonardo:
            model_id = ImagenManager.get_models_info('Flux Dev')
            for prompt in prompt_list:
                imagen_id = ImagenManager.LeonardoAPI(
                    num_of_images=1,
                    imagen_prompt=prompt["prompt_use"],
                    height=768,
                    width=1376,
                    modelId=model_id
                )
                time.sleep(10)  # Để tránh quá tải API
                if imagen_id: 
                    output_file, url_imagen = ImagenManager.get_imagen(imagen_id, id, prompt["num_of_image"])
                    if output_file and url_imagen:
                        logging.info(f"[IMAGEN] Scene {prompt['num_of_image']} processed successfully.")
                    else:
                        logging.error(f"[IMAGEN] Failed to process Scene {prompt['num_of_image']}.")
                    out_list.append({
                        "num_of_image": prompt["num_of_image"],
                        "output_file": output_file,
                        "url_imagen": url_imagen
                    })
                else:
                    logging.error(f"[IMAGEN] Failed to generate image for Scene {prompt['num_of_image']}.")
        if is_gpt:
            for prompt in prompt_list:
                output_file, url_imagen = ImagenManager.GPT_imagen_1(
                    prompt=prompt["prompt_use"],
                    id=id,
                    scene_number=prompt["num_of_image"]
                )
                if output_file and url_imagen:
                    logging.info(f"[IMAGEN] Scene {prompt['num_of_image']} processed successfully.")
                else:
                    logging.error(f"[IMAGEN] Failed to process Scene {prompt['num_of_image']}.")
                out_list.append({
                    "num_of_image": prompt["num_of_image"],
                    "output_file": output_file,
                    "url_imagen": url_imagen
                })
        if is_gemini:
            for prompt in prompt_list:
                time.sleep(10)  # Để tránh quá tải API
                output_file, url_imagen = ImagenManager.GGAIStudio_imagen(
                    prompt=prompt["prompt_use"],
                    id=id,
                    scene_number=prompt["num_of_image"]
                )
                if output_file and url_imagen:
                    logging.info(f"[IMAGEN] Scene {prompt['num_of_image']} processed successfully.")
                else:
                    logging.error(f"[IMAGEN] Failed to process Scene {prompt['num_of_image']}.")
                out_list.append({
                    "num_of_image": prompt["num_of_image"],
                    "output_file": output_file,
                    "url_imagen": url_imagen
                })
        # logging.info(f"{out_list}")
        logging.info(f"[IMAGEN] Image generation process completed for ID : {id}")
        return out_list

    

if __name__ == "__main__":
#     scene = {
#     "scene_number": 1,
#     "description": "A young boy and his father tending sheep in a misty valley.",
#     "start_in": "The morning mist, soft and cool,",
#     "dominant_emotion": "serenity",
#     "scene_type": "wide shot",
#     "location_time": "Bulgarian village, dawn, early 16th century",
#     "emotional_intensity": 2,
#     "visual_style": "16th-century Eastern European folk art",
#     "color_palette": "soft blues, greens, and grays with hints of dawn pink"
#   }
#     num, prompt = PromptManager._format_prompt_imagen(scene)
#     print ( f"Scene Number: {num}\nPrompt: {prompt}")
    import os
    import sys
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(project_root)
    from database.datacontrol import S2PModule
    from models.s2pmodel import ImagenData
    out_list= []
    for i in range(1, 41):
        scene_number = i
        p = r"D:\Tan.n-AIEngineer\Program\Video-render-order-theta\app\database\Imagen\10015"
        i_path = f"10015_scene_{scene_number}_gemini.png"
        full_path = Path(f"{p}\\{i_path}")
        print(full_path)
        if full_path.exists():
            output_file = f"{SERVER_HOST}/database/Imagen/10015/{i_path}"
            out_list.append({
                        "num_of_image": scene_number,
                        "output_file": output_file,
                        "url_imagen": output_file
                    })
    print(out_list)
    data = ImagenData(
        id=10015,
        uuid="37561aaefe1c464ebf1314c90a75968e",
        script="",
        status="done",
        images_path=out_list,
        created_at=datetime.now().isoformat()
        )
    S2PModule.write_or_update_data(data.model_dump(),10015)
    
    