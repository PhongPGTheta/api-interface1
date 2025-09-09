import os
import subprocess
import logging
from pathlib import Path
from natsort import natsorted
from PIL import Image
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
from core.config import DATA_AUDIO_PATH, DATA_IMAGEN_PATH, DATA_VIDEO_PATH, DATA_TEMP
from mutagen.mp3 import MP3
from mutagen.wave import WAVE

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

class ReSizeManager:
    TARGET_RATIO = 16 / 9
    TARGET_RESOLUTION = (1280, 720)  # hoặc 1920x1080 nếu bạn muốn 2K/FullHD

    @staticmethod
    def fix_image_aspect_ratio(image_path: Path) -> None:
        try:
            img = Image.open(image_path)
            w, h = img.size
            current_ratio = w / h
            target_ratio = ReSizeManager.TARGET_RATIO
            target_w, target_h = ReSizeManager.TARGET_RESOLUTION

            # === 1. Nếu gần đúng 16:9 và chỉ cần resize về đúng độ phân giải
            if abs(current_ratio - target_ratio) < 0.05:
                img = img.resize((target_w, target_h), Image.LANCZOS)

            # === 2. Nếu là hình vuông → crop giữa
            elif w == h:
                new_w = w
                new_h = int(w / target_ratio)
                if new_h > h:
                    new_h = h
                    new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                top = (h - new_h) // 2
                img = img.crop((left, top, left + new_w, top + new_h))
                img = img.resize((target_w, target_h), Image.LANCZOS)

            # === 3. Nếu ảnh ngang quá dài → crop hai bên
            elif current_ratio > target_ratio:
                new_w = int(h * target_ratio)
                left = (w - new_w) // 2
                img = img.crop((left, 0, left + new_w, h))
                img = img.resize((target_w, target_h), Image.LANCZOS)

            # === 4. Nếu ảnh đứng hoặc ngắn → crop trên dưới hoặc resize nhỏ
            else:
                new_h = int(w / target_ratio)
                top = (h - new_h) // 2
                img = img.crop((0, top, w, top + new_h))
                img = img.resize((target_w, target_h), Image.LANCZOS)

            # === 5. Đảm bảo chia hết cho 2
            final_w, final_h = img.size
            if final_w % 2 != 0 or final_h % 2 != 0:
                img = img.resize((final_w // 2 * 2, final_h // 2 * 2), Image.LANCZOS)

            img.save(image_path)
            logging.info(f"[IMAGE] Fixed: {image_path.name} → {img.size}")
        except Exception as e:
            logging.warning(f"[IMAGE] Failed to process {image_path.name}: {str(e)}")

class RenderManager:
    @staticmethod
    def render_from_folder(image_folder, audio_folder, id: int, uuid: str = None):
        logging.info("[RENDER] Start rendering process...")

        # audio_folder = Path(r"D:\Tan.n-AIEngineer\Program\Video-render-order-theta\app\database\Audio") / f"{id}"
        # image_folder = Path(r"D:\Tan.n-AIEngineer\Program\Video-render-order-theta\app\database\Imagen") / f"{id}"
        # video_folder = Path(r"D:\Tan.n-AIEngineer\Program\Video-render-order-theta\app\database\VideoGen") / f"{id}"
        audio_folder = Path(audio_folder)
        image_folder = Path(image_folder)
        if not audio_folder.exists() and image_folder.exists():
            audio_folder = Path(DATA_AUDIO_PATH) / f"{id}"
            image_folder = Path(DATA_IMAGEN_PATH) / f"{id}"
        video_folder = Path(DATA_VIDEO_PATH) / f"{id}"
        ffmpeg_file = r"E:\python\Video-render-order-theta\app\bin\ffmpeg.exe"
        video_folder.mkdir(parents=True, exist_ok=True)

        # === Step 1: Load audio ===
        audio_file = None
        for ext in [".wav", ".mp3"]:
            candidate = audio_folder / f"{id}{ext}"
            if candidate.exists():
                audio_file = candidate
                break
        if not audio_file:
            raise FileNotFoundError(f"[AUDIO] No audio file found for ID {id} in {audio_folder}")
        logging.info(f"[AUDIO] Found audio file: {audio_file.name}")

        audio = MP3(audio_file) if audio_file.suffix == ".mp3" else WAVE(audio_file)
        audio_duration = audio.info.length
        logging.info(f"[AUDIO] Duration: {audio_duration:.2f} seconds")

        # === Step 2: Load images ===
        image_exts = ["*.jpg", "*.jpeg", "*.png", "*.JPG", "*.JPEG", "*.PNG"]
        image_files = []
        for ext in image_exts:
            image_files += list(image_folder.glob(ext))
        image_files = natsorted(image_files)

        if not image_files:
            raise FileNotFoundError("[IMAGE] No image files found.")
        duration_per_image = audio_duration / len(image_files)
        logging.info(f"[IMAGE] Found {len(image_files)} images → {duration_per_image:.2f}s per image")

        # Resize images
        for img in image_files:
            ReSizeManager.fix_image_aspect_ratio(img)

        # === Step 3: Create list.txt
        list_file = Path(DATA_TEMP) / f"{id}_list.txt"
        with open(list_file, "w", encoding="utf-8") as f:
            for img in image_files:
                f.write(f"file '{img.resolve()}'\n")
                f.write(f"duration {duration_per_image:.4f}\n")
            # Optional: hold last image longer
            f.write(f"file '{image_files[-1].resolve()}'\n")

        # === Step 4: Render video from image sequence
        temp_video = Path(DATA_TEMP) / f"{id}_rendered_temp.mp4"
        subprocess.run([
            ffmpeg_file, "-y",
            "-f", "concat",
            "-safe", "0",
            "-fflags", "+genpts",
            "-i", str(list_file),
            "-fps_mode", "vfr",
            "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-pix_fmt", "yuv420p",
            str(temp_video)
        ], check=True)

        # === Step 5: Merge audio ===
        # Use UUID in filename to make each video unique
        if uuid:
            output_file = video_folder / f"{uuid}.mp4"
        else:
            output_file = video_folder / f"{id}.mp4"
        logging.info("[RENDER] Merging video with audio...")
        subprocess.run([
            ffmpeg_file, "-y",
            "-i", str(temp_video),
            "-i", str(audio_file),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-af", "volume=2.0",
            str(output_file)
        ], check=True)

        # os.remove(temp_video)
        # os.remove(list_file)
        logging.info(f"[RENDER] ✅ Finished! Video saved to: {output_file.resolve()}")
        return output_file.resolve()

class VideoManager:
    @staticmethod
    def process_video(image_folder, audio_folder, id: str, uuid: str = None):
        video_path = RenderManager.render_from_folder(image_folder, audio_folder, id, uuid)
        if video_path.exists():
            logging.info("[RENDER] Final Video Generate sucessfully!")
            return video_path
        else: 
            return None
        
        
if __name__ == "__main__":
    VideoManager.process_video(10014)