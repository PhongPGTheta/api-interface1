
from contextlib import contextmanager
from datetime import datetime
from google import genai
from google.cloud import texttospeech
import google.generativeai as ggenai
from google.genai import types
from pathlib import Path
import logging
import threading
import subprocess
import requests
import base64
import random
import time
import json
import wave
import copy
import re
import os
from core.test import resource_path
import sys
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)
from core.elevenlabs import CheckProxy
from core.promptcontrol import SYS_PROMPT_CHECK_AND_REWRITE
from core.elevenlabs import API_KEY, PROXY_URL, HISTORY_VOICE_ID_PATH
from core.config import GOOGLE_API_KEY,\
        GOOGLE_API_KEY_AUDIO, DATA_TEMP,\
        SERVICE_ACCOUNT_KEY
from .upload2drive import UploadToDrive
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = SERVICE_ACCOUNT_KEY

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)

class AccountManager:
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Safari/605.1.15'
    ]
    ACCEPT_LANGUAGES = [
        'en-US,en;q=0.9', 'en-GB,en;q=0.9', 'en-CA,en;q=0.9', 'en-AU,en;q=0.9', 'en-NZ,en;q=0.9'
    ]

    @staticmethod
    def get_random_headers(api_key):
        user_agent = random.choice(AccountManager.USER_AGENTS)
        accept_language = random.choice(AccountManager.ACCEPT_LANGUAGES)
        platform = "Windows" if "Windows" in user_agent else ("Macintosh" if "Macintosh" in user_agent else "Linux")
        headers = {
            'User-Agent': user_agent,
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
            'Accept-Language': accept_language,
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Origin': 'https://elevenlabs.io',
            'Referer': 'https://elevenlabs.io/',
            'xi-api-key': api_key
        }
        return headers

    @staticmethod
    def check_credit(account_name, api_key):
        try:
            url = "https://api.elevenlabs.io/v1/user"
            headers = {"xi-api-key": api_key}
            response = requests.get(url=url, headers=headers)

            if response.status_code != 200:
                logging.error(f"[AUDIO] Failed to fetch credit for {account_name[:10]} - Status: {response.status_code}")
                return None

            data = response.json()
            count = int(data["subscription"]["character_count"])
            limit = int(data["subscription"]["character_limit"])
            credit = limit - count

            logging.info(f"[CREDIT] Account {account_name[:10]} | Used: [{count} / {limit}] | Remaining: {credit}")
            return {
                "name": account_name,
                "api_key": api_key,
                "credit": credit
            }

        except Exception as e:
            logging.error(f"[AUDIO] Check credit for account {account_name[:10]} failed: {e}")
            return None

    @staticmethod
    def add_random_delay(min_delay=5.0, max_delay=10.0):
        time.sleep(random.uniform(min_delay, max_delay))

    @staticmethod
    @contextmanager
    def temporary_proxy(proxy_url):
        logging.info(f"[PROXY] Checking proxy for using : {proxy_url[:10]}")
        original_http_proxy = os.environ.get('HTTP_PROXY')
        original_https_proxy = os.environ.get('HTTPS_PROXY')
        if proxy_url:
            if not proxy_url.startswith(('http://', 'https://')):
                proxy_url = 'http://' + proxy_url
            os.environ['HTTP_PROXY'] = proxy_url
            os.environ['HTTPS_PROXY'] = proxy_url
        try:
            yield
        finally:
            if original_http_proxy is None:
                os.environ.pop('HTTP_PROXY', None)
            else:
                os.environ['HTTP_PROXY'] = original_http_proxy
            if original_https_proxy is None:
                os.environ.pop('HTTPS_PROXY', None)
            else:
                os.environ['HTTPS_PROXY'] = original_https_proxy

    AUDIO_TEMP_DIR = Path(resource_path("database/Temp"))
    AUDIO_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_temp_file_path():
        now = datetime.now()
        return AccountManager.AUDIO_TEMP_DIR / f"{now.month}_{now.year}_credit_temp.json"
    
    @staticmethod
    def load_credit_to_update(account_name: str = None, api_key: str = None, credit: int = None):
        path_temp = AccountManager.get_temp_file_path()
        accounts_info = []

        # Nếu chưa có file cache và chưa truyền thông tin, tạo mới toàn bộ
        if not path_temp.exists() and not (account_name and api_key and credit is not None):
            logging.info("[CREDIT] Temp file not found. Checking credits for all accounts...")
            for acc in API_KEY:
                info = AccountManager.check_credit(acc["name"], acc["api_key"])
                if not info or not isinstance(info, dict):
                    logging.warning(f"[CREDIT] Skipping {acc['name']} due to invalid info.")
                    continue
                info.update({
                    "last_update": datetime.now().isoformat(),
                    "status": "ready" if info["credit"] > 10 else "stop use"
                })
                accounts_info.append(info)
            with open(resource_path(path_temp), "w", encoding="utf-8") as f:
                json.dump(accounts_info, f, ensure_ascii=False, indent=2)
            logging.info(f"[CREDIT] Cached credit info for {len(accounts_info)} accounts.")
            return accounts_info

        # Nếu file đã có, chỉ cập nhật nếu truyền vào account
        if path_temp.exists():
            with open(resource_path(path_temp), "r+", encoding="utf-8") as f:
                accounts_info = json.load(f)

                # Nếu có truyền tên + key, cập nhật
                if account_name and api_key:
                    logging.info(f"[CREDIT] Updating info for account: {account_name}")
                    
                    if credit is None:
                        info = AccountManager.check_credit(account_name, api_key)
                        if not info or not isinstance(info, dict):
                            logging.warning(f"[CREDIT] Skipping update for {account_name} - check failed.")
                            return accounts_info
                        credit = info["credit"]

                    updated = False
                    for acc in accounts_info:
                        if acc["api_key"] == api_key:
                            acc.update({
                                "credit": credit,
                                "last_update": datetime.now().isoformat(),
                                "status": "ready" if credit > 10 else "stop use"
                            })
                            updated = True
                            break
                    if not updated:
                        accounts_info.append({
                            "name": account_name,
                            "api_key": api_key,
                            "credit": credit,
                            "last_update": datetime.now().isoformat(),
                            "status": "ready" if credit > 10 else "stop use"
                        })

                    # Ghi lại
                    f.seek(0)
                    f.truncate()
                    json.dump(accounts_info, f, ensure_ascii=False, indent=2)
                    logging.info(f"[CREDIT] Saved updated credit info for: {account_name}")

        return accounts_info


    @staticmethod
    def get_random_account():
        path_temp = AccountManager.get_temp_file_path()
        if not path_temp.exists():
            logging.error("[CREDIT] Credit cache not found.")
            return None

        with open(resource_path(path_temp), 'r', encoding='utf-8') as f:
            accounts = json.load(f)

        ready_accounts = [acc for acc in accounts if acc.get("status") == "ready"]

        if not ready_accounts:
            logging.warning("[CREDIT] No available account with status 'ready'.")
            return None

        return random.choice(ready_accounts)  # Trả lại cả dict acc gồm name, api_key, credit,...

class ElevenLabsManager:
    SEGMENTS = []
    @staticmethod
    def fetch_and_save_all_voice_ids(api_key, proxy_url, save_path=None):
        url = "https://api.elevenlabs.io/v1/voices"
        headers = AccountManager.get_random_headers(api_key)
        with AccountManager.temporary_proxy(proxy_url):
            resp = requests.get(url, headers=headers, timeout=15)
        AccountManager.add_random_delay()
        if resp.status_code == 200:
            data = resp.json()
            voices = data.get('voices', [])
            voice_ids = [v['voice_id'] for v in voices]
            # Lưu vào file
            if save_path is None:
                save_path = Path(resource_path(HISTORY_VOICE_ID_PATH))
            else:
                save_path = Path(resource_path(save_path))
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(resource_path(save_path), "w", encoding="utf-8") as f:
                json.dump({"voice_ids": voice_ids}, f, ensure_ascii=False, indent=2)
            logging.info(f"Fetched and saved {len(voice_ids)} voice_ids.")
            return voice_ids
        else:
            logging.error(f"Failed to fetch voices: {resp.status_code} {resp.text}")
            raise Exception(f"Failed to fetch voices: {resp.status_code} {resp.text}")

    @staticmethod
    def convert_tts(text, api_key, proxy_url, voice_id, output_path, model_id="eleven_multilingual_v2"):
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = AccountManager.get_random_headers(api_key)
        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": {"stability": 0.7, "similarity_boost": 0.75}
        }
        with AccountManager.temporary_proxy(proxy_url):
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
        AccountManager.add_random_delay(2, 5)
        if resp.status_code == 200:
            with open(resource_path(output_path), "wb") as f:
                f.write(resp.content)
            logging.info(f"Saved TTS audio to {output_path}")
            return output_path
        else:
            logging.error(f"TTS failed: {resp.status_code} {resp.text}")
            raise Exception(f"TTS failed: {resp.status_code} {resp.text}")

    @staticmethod
    def get_segments(text, credit_limit=None, hard_word_limit=1000):
        def safe_cut(text, max_chars):
            """Cắt đoạn text đến dấu '.' gần nhất mà không vượt quá max_chars."""
            if len(text) <= max_chars:
                return text, ''
            cut = text[:max_chars]
            last_dot = cut.rfind(".")
            if last_dot == -1:
                # Nếu không có dấu chấm, cắt cứng
                return cut, text[max_chars:]
            return cut[:last_dot+1], text[last_dot+1:]

        if not ElevenLabsManager.SEGMENTS:
            # Lần đầu gọi hàm, chia theo dòng
            ElevenLabsManager.SEGMENTS = [seg.strip() for seg in text.splitlines() if seg.strip()]

        while ElevenLabsManager.SEGMENTS:
            current = ElevenLabsManager.SEGMENTS[0]

            # Nếu đoạn hiện tại thỏa mãn giới hạn credit/hard_word_limit, trả luôn
            if len(current) <= credit_limit and len(current.split()) <= hard_word_limit:
                return ElevenLabsManager.SEGMENTS.pop(0)

            # Nếu đoạn hiện tại vượt quá credit_limit, chia nhỏ
            if len(current) > credit_limit:
                passage, remaining = safe_cut(current, credit_limit)

                if len(passage) > credit_limit:
                    # Đoạn cắt ra vẫn vượt quá credit_limit, skip account
                    logging.warning(f"[SEGMENT] Đoạn quá dài vượt credit_limit ({len(passage)} > {credit_limit}). Cần đổi account.")
                    return None

                # Cập nhật SEGMENTS: đoạn sau thêm vào đầu danh sách
                ElevenLabsManager.SEGMENTS[0] = remaining.strip()
                if not ElevenLabsManager.SEGMENTS[0]:
                    ElevenLabsManager.SEGMENTS.pop(0)  # Nếu phần còn lại rỗng, xoá luôn

                if passage.strip():
                    return passage.strip()

            else:
                # Đoạn không dài hơn credit, nhưng quá nhiều từ
                return ElevenLabsManager.SEGMENTS.pop(0)

        # Không còn gì để xử lý
        return None


class MergeAudio:
    @staticmethod
    def check_audio_file(path: Path) -> dict:
        ffprobe_path = r"E:\python\Video-render-order-theta\app\bin\ffprobe.exe"
        """Kiểm tra file audio bằng ffprobe và trả về thông tin định dạng"""
        if not path.exists() or path.stat().st_size == 0:
            logging.warning(f"[FFPROBE] File missing or empty: {path}")
            return {"valid": False}

        cmd = [
            ffprobe_path,
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=sample_rate,channels,codec_name,duration",
            "-of", "json",
            str(path)
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            info = json.loads(result.stdout)

            if "streams" not in info or not info["streams"]:
                logging.warning(f"[FFPROBE] No audio stream found: {path}")
                return {"valid": False}

            stream = info["streams"][0]
            return {
                "valid": True,
                "sample_rate": int(stream.get("sample_rate", 0)),
                "channels": int(stream.get("channels", 0)),
                "codec": stream.get("codec_name", ""),
                "duration": float(stream.get("duration", 0)),
            }

        except subprocess.CalledProcessError as e:
            logging.error(f"[FFPROBE] Error probing file: {path}\n{e.stderr}")
            return {"valid": False}

    @staticmethod
    def merge(audio_dir, temp_files, id: int):
        audio_dir = Path(resource_path(audio_dir))
        ffmpeg_path = Path(resource_path(r"E:\python\Video-render-order-theta\app\bin\ffmpeg.exe")).resolve()
        ext = ".mp3" if any(str(f).endswith(".mp3") for f in temp_files) else ".wav"
        silence_1s = audio_dir / f"silence1s{ext}"
        filelist_path = audio_dir / f"{id}_filelist.txt"
        merged_file = audio_dir / f"{id}{ext}"
        audio_dir.mkdir(parents=True, exist_ok=True)
        if merged_file.exists():
            os.remove(merged_file)
            logging.info("[MERGE] There is an old Merge file -> Delete the old processed file.")
        # Log info từng file
        for f in audio_dir.glob(f"*{ext}"):
            info = MergeAudio.check_audio_file(f)
            log = f"{f.name}: {info['codec']} - {info['sample_rate']}Hz - {info['channels']}ch - {info['duration']:.2f}s" if info["valid"] else f"{f.name}: INVALID"
            logging.info(log) if info["valid"] else logging.warning(log)

        # Tạo silence nếu chưa có
        if not silence_1s.exists():
            silence_cmd = [
                str(ffmpeg_path), "-f", "lavfi",
                "-i", f"anullsrc=r=24000:cl=mono",
                "-t", "1",
            ]
            
            if ext == ".mp3":
                silence_cmd += ["-acodec", "libmp3lame", "-q:a", "9"]
            else:
                silence_cmd += ["-acodec", "pcm_s16le"]

            silence_cmd.append(str(silence_1s))

            logging.info(f"[MERGE] Creating silence file:\n{' '.join(silence_cmd)}")
            r = subprocess.run(silence_cmd, capture_output=True, text=True)
            if r.returncode != 0:
                logging.error(f"[MERGE] Failed to create silence: {r.stderr}")
                raise Exception("Failed to create silence")

        with open(resource_path(filelist_path), "w", encoding="utf-8") as f:
            f.write(f"file '{silence_1s.resolve().as_posix()}'\n")
            for name in temp_files:
                path = audio_dir / name
                logging.info(f"[MERGE] Adding: {path}")
                if not path.exists() or path.stat().st_size == 0:
                    logging.warning(f"[MERGE] Missing or empty file: {path}")
                f.write(f"file '{path.resolve().as_posix()}'\n")
            f.write(f"file '{silence_1s.resolve().as_posix()}'\n")

        # Sau khi ghi xong, log toàn bộ filelist để debug:
        with open(resource_path(filelist_path), "r", encoding="utf-8") as f:
            logging.info(f"[MERGE] Filelist content:\n{f.read()}")

        # Merge
        merge_cmd = [
            str(ffmpeg_path), "-f", "concat", "-safe", "0",
            "-i", str(filelist_path),
            "-filter:a", "atempo=0.9",
            "-ar", "24000", "-ac", "1",
            "-c:a", "libmp3lame" if ext == ".mp3" else "pcm_s16le",
            str(merged_file)
        ]
        logging.info(f"[MERGE] Running FFmpeg:\n{' '.join(merge_cmd)}")
        r = subprocess.run(merge_cmd, capture_output=True, text=True)
        if r.returncode != 0:
            logging.error(f"[MERGE] FFmpeg merge failed: {r.stderr}")
            raise Exception("FFmpeg merge failed")
        logging.info("[AUDIO] Merge is Processing ....")
        logging.info(f"[AUDIO] Final audio saved to {merged_file}")
        return str(merged_file)

class ContentSafety:
    @staticmethod
    def run_safety_check_and_rewrite(text_segment: str) -> tuple:
        ggenai.configure(api_key=GOOGLE_API_KEY)
        prompt = SYS_PROMPT_CHECK_AND_REWRITE.replace("[TEXT]", text_segment.strip())
        model = ggenai.GenerativeModel("gemini-2.5-flash")

        try:
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[len("```json"):].strip()

            if result_text.endswith("```"):
                result_text = result_text[:-3].strip()
            # Kiểm tra phản hồi có đúng JSON format không
            if not result_text.startswith("{"):
                logging.error("[ERROR] Gemini did not return valid JSON.")
                logging.error(f"[DEBUG Gemini output]: {result_text[:200]}")
                return text_segment, []

            # Parse kết quả JSON
            data = json.loads(result_text)
            logging.info("[SAFETY] Safe - Continue to Convert Text to Sound.")
            cleaned_text = data.get("cleaned_text", text_segment).strip()
            blocked_keywords = data.get("blocked_keywords", [])

            return cleaned_text, blocked_keywords

        except Exception as e:
            logging.info("[NOT SAFETY] Continue without Checking Safety segment.")
            return text_segment, []
    
    @staticmethod
    def log_blocked_keywords(segment_id: str, blocked_keywords: list):
        if not blocked_keywords:
            return
        log_path = Path(DATA_TEMP) / "blocked_keywords.json"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            if log_path.exists():
                with open(resource_path(log_path), "r", encoding="utf-8") as f:
                    existing = json.load(f)
            else:
                existing = {}

            existing[segment_id] = blocked_keywords

            with open(resource_path(log_path), "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)

        except Exception as e:
            print(f"[ERROR logging keywords]: {e}")

class AudioService:
    @staticmethod
    def Process_segment_to_audio(transcript, audio_dir, id=""):
        if not transcript:
            logging.error("Transcript is empty!")
            raise ValueError("Transcript is empty!")

        logging.info("[AUDIO] Start processing transcript to audio")
        AccountManager.load_credit_to_update()

        audio_dir = Path(resource_path(audio_dir))
        audio_dir.mkdir(parents=True, exist_ok=True)
        temp_files = []

        total_words = len(transcript.split())
        total_processed_words = 0

        # Hàm lấy account và voice ID một lần duy nhất
        def get_voice_id_once():
            while True:
                account = AccountManager.get_random_account()
                if not account:
                    raise Exception("No working account left.")
                api_key = account["api_key"]
                account_name = account["name"]
                credit_limit = account["credit"]

                tried_proxies = set()
                while len(tried_proxies) < len(PROXY_URL):
                    proxy = random.choice([p for p in PROXY_URL if p not in tried_proxies])
                    tried_proxies.add(proxy)
                    try:
                        voice_ids = ElevenLabsManager.fetch_and_save_all_voice_ids(api_key, proxy)
                        if not voice_ids:
                            raise Exception("Empty voice list.")
                        voice_id = random.choice(voice_ids)
                        return account_name, api_key, credit_limit, voice_id
                    except Exception as e:
                        logging.warning(f"[AUDIO] Failed to fetch voices using proxy {proxy[:20]}...: {e}")
                # Thử proxy xong nhưng vẫn fail → thử account khác

        account_name, api_key, credit_limit, voice_id = get_voice_id_once()

        index = 0
        while total_processed_words < total_words:
            # Tự ngắt nếu hết credit tài khoản hiện tại
            if credit_limit <= 150:
                logging.warning(f"[CREDIT] Account {account_name} is low on credit ({credit_limit}). Switching account...")
                while True:
                    account = AccountManager.get_random_account()
                    if not account:
                        raise Exception("No working account left.")
                    api_key = account["api_key"]
                    account_name = account["name"]
                    credit_limit = account["credit"]
                    if credit_limit > 150:
                        break

            # Cắt từng đoạn theo credit_limit và số còn lại
            remaining_text = " ".join(transcript.split()[total_processed_words:])
            segment = ElevenLabsManager.get_segments(remaining_text, credit_limit=credit_limit)
            if not segment:
                break  # Hết đoạn hoặc lỗi chia

            index += 1
            percent = int((total_processed_words / total_words) * 100)
            logging.info(f"[AUDIO] Processing segment {index} - Progress: {percent}%")

            success = False
            tried_proxies = set()

            while not success:
                proxy = random.choice([p for p in PROXY_URL if p not in tried_proxies])
                tried_proxies.add(proxy)
                try:
                    temp_path = str(audio_dir / f"{id}_part_{index}.wav")
                    ElevenLabsManager.convert_tts(segment, api_key, proxy, voice_id, temp_path)
                    temp_files.append(temp_path)

                    used_credit = len(segment)
                    total_processed_words += len(segment.split())
                    credit_limit -= used_credit
                    AccountManager.load_credit_to_update(account_name, api_key, credit=credit_limit)

                    logging.info(f"[AUDIO] Finished segment {index} using proxy: {proxy[:20]}... and account: {account_name}")
                    success = True

                except Exception as e:
                    logging.warning(f"[AUDIO] Proxy or TTS failed ({proxy[:20]}...) for account {account_name}: {e}")
                    if ("quota" in str(e).lower() or "voice" in str(e).lower() or "403" in str(e)) or len(tried_proxies) >= len(PROXY_URL):
                        logging.warning("[AUDIO] Retrying with new account (voice remains unchanged)...")
                        while True:
                            account = AccountManager.get_random_account()
                            if not account:
                                raise Exception("No working account left.")
                            api_key = account["api_key"]
                            account_name = account["name"]
                            credit_limit = account["credit"]
                            if credit_limit > 150:
                                break
                        tried_proxies.clear()

        # Sau khi xử lý xong tất cả segment, mới merge và return
        merged_path = MergeAudio.merge(audio_dir, temp_files, id=id)
        logging.info(f"[AUDIO] Created audio successfully: {merged_path}")
        return merged_path
    
    @staticmethod
    def process_tts_cloud(segment: str, audio_dir: str, id: int, idx: int) -> Path:
        logging.info(f"[TTS] Starting synthesis for ID {id} - part {idx}")
        
        try:
            client = texttospeech.TextToSpeechClient()

            synthesis_input = texttospeech.SynthesisInput(text=segment)

            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Chirp3-HD-Orus",
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=0.85,
                sample_rate_hertz=24000
            )

            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            output_path = Path(resource_path(audio_dir)) / f"{id}_tts_{idx}.mp3"
            with open(resource_path(output_path), "wb") as out:
                out.write(response.audio_content)

            logging.info(f"[TTS] Saved TTS audio: {id}_part_{idx}.mp3")
            
        except Exception as e:
            logging.error(f"[TTS] Failed for ID {id} part {idx}: {e}")
            raise

    @staticmethod
    def is_proxy_alive(proxy):
        try:
            proxies = {"http": proxy, "https": proxy}
            response = requests.get("https://www.google.com", proxies=proxies, timeout=6)
            return response.status_code == 200
        except Exception as e:
            logging.warning(f"[AUDIO] Proxy test failed: {proxy} | {e}")
            return False

    @staticmethod
    def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
        with wave.open(resource_path(str(filename)), "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)

    @staticmethod
    def _generate_with_curl(content, api_key, proxy, file_path, timeout):
        prompt = (
            "Use a natural, deep male voice. Speak slowly and calmly, as if reading a gentle bedtime story. "
            "Avoid sounding robotic or childlike. Speak clearly and softly. Say: " + content.strip()
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": "Orus"
                        }
                    }
                }
            },
            "model": "gemini-2.5-flash-preview-tts"
        }
        json_payload = json.dumps(payload)

        proxies_pool = copy.deepcopy(PROXY_URL)
        random.shuffle(proxies_pool)

        # Ưu tiên proxy đầu tiên nếu có
        if proxy and proxy in proxies_pool:
            proxies_pool.remove(proxy)
        proxies_pool.insert(0, proxy)

        for attempt, current_proxy in enumerate(proxies_pool[:5], 1):  # tối đa 5 proxy
            curl_cmd = [
                "curl", "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent",
                "-H", f"x-goog-api-key: {api_key}",
                "-X", "POST",
                "-H", "Content-Type: application/json",
                "-d", json_payload,
                "--silent", "--show-error"
            ]

            if current_proxy:
                proxy_clean = current_proxy.replace("http://", "")
                if "@" in proxy_clean:
                    creds, addr = proxy_clean.split("@")
                    curl_cmd.extend(["--proxy", f"http://{addr}"])
                    curl_cmd.extend(["--proxy-user", creds])
                else:
                    curl_cmd.extend(["--proxy", f"http://{proxy_clean}"])

            logging.info(f"[AUDIO] Attempt {attempt} using proxy: {current_proxy} | Target: {file_path.name}")

            try:
                result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=timeout)
                result.check_returncode()

                try:
                    res_json = json.loads(result.stdout)
                except Exception:
                    logging.error(f"[AUDIO] JSON parse error: {result.stdout.strip()}")
                    continue

                if res_json.get("promptFeedback", {}).get("blockReason"):
                    logging.error(f"[AUDIO] Blocked by Gemini: {res_json['promptFeedback']['blockReason']}")
                    return

                candidates = res_json.get("candidates", [])
                if not candidates:
                    continue

                try:
                    b64data = candidates[0]["content"]["parts"][0]["inlineData"]["data"]
                    raw = base64.b64decode(b64data)
                    AudioService.wave_file(file_path, raw)
                    logging.info(f"[AUDIO] Saved: {file_path}")
                    return
                except Exception as e:
                    logging.error(f"[AUDIO] Error parsing audio: {e}")
                    continue

            except subprocess.TimeoutExpired:
                logging.warning(f"[AUDIO] Timeout with proxy: {current_proxy}")
            except subprocess.CalledProcessError as e:
                if "407" in (e.stderr or ""):
                    logging.warning(f"[AUDIO] Proxy 407 error: {current_proxy}")
                else:
                    logging.error(f"[AUDIO] curl failed: {e.stderr.strip()}")
            # tiếp tục thử proxy khác


    @staticmethod
    def process_ggai_studio(content, audio_dir, id, idx, api_key, proxy, timeout):
        filename = Path(resource_path(audio_dir)) / f"{id}_part_{idx}.wav"
        clean_content, blockkey =ContentSafety.run_safety_check_and_rewrite(content)
        ContentSafety.log_blocked_keywords(f"{id}_segment_{idx}",blockkey)
        AudioService._generate_with_curl(clean_content, api_key, proxy, filename, timeout=timeout)

    @staticmethod

    def process_audio(transcript, audio_dir, id=""):
        audio_dir = Path(resource_path(audio_dir)) / f"{id}"
        audio_dir.mkdir(parents=True, exist_ok=True)

        contents = [c.strip() for c in transcript.split("\n") if c.strip()]
        CheckProxy.run()
        # Kiểm tra và chia đoạn cuối nếu > 2000 từ
        if contents:
            last = contents[-1]
            if len(last.split()) > 2000:
                words = last.split()
                chunk_size = len(words) // 3
                split_contents = []
                start = 0
                for i in range(2):
                    end = start + chunk_size
                    while end < len(words) and not words[end].endswith('.'):
                        end += 1
                    split_contents.append(' '.join(words[start:end + 1]))
                    start = end + 1
                split_contents.append(' '.join(words[start:]))
                contents = contents[:-1] + split_contents

        logging.info(f"[AUDIO] Split transcript into {len(contents)} parts")

        batch_size = 4
        threads = []
        idx = 1
        api_keys = GOOGLE_API_KEY_AUDIO.copy()
        proxies = PROXY_URL.copy()
        random.shuffle(api_keys)
        random.shuffle(proxies)
        usage_log = {}

        # Tạo audio cho từng đoạn
        for content in contents:
            proxy = None
            while proxies:
                candidate = proxies[idx % len(proxies)]
                if AudioService.is_proxy_alive(candidate):
                    proxy = candidate
                    break
                else:
                    logging.warning(f"[AUDIO] Removed error proxy: {candidate}")
                    proxies.remove(candidate)
            if not proxy:
                logging.error("[AUDIO] No working proxies available. Abort.")
                break
            api_key = api_keys[idx % len(api_keys)]['key']
            key_name = api_keys[idx % len(api_keys)]['name']
            delay = round(len(content) * 0.07, 2)
            logging.info(f"[AUDIO] Generating part {idx} | Len={len(content)} | Delay={delay}s")
            t = threading.Thread(
                target=AudioService.process_ggai_studio,
                args=(content, audio_dir, id, idx, api_key, proxy, delay)
            )
            t.start()
            threads.append((t, delay, idx))
            usage_log[key_name] = usage_log.get(key_name, 0) + 1
            if len(threads) >= batch_size:
                for t, delay, _ in threads:
                    t.join(timeout=delay + 5)
                threads.clear()
            idx += 1

        # Đợi các thread cuối cùng
        for t, delay, _ in threads:
            t.join(timeout=delay + 5)


        # Lưu các đoạn content đã chia ra file JSON để người dùng có thể tự lấy và gen audio
        try:
            content_json_path = Path(DATA_TEMP) / f"audio_parts_{id}.json"
            content_json_path.parent.mkdir(parents=True, exist_ok=True)
            content_json = [{"part": i+1, "content": contents[i]} for i in range(len(contents))]
            with open(resource_path(content_json_path), "w", encoding="utf-8") as f:
                json.dump(content_json, f, ensure_ascii=False, indent=2)
            logging.info(f"[AUDIO] Saved split audio contents to {content_json_path}")
        except Exception as e:
            logging.warning(f"[AUDIO] Failed to save split audio contents: {e}")

        # Kiểm tra số lượng file audio đã tạo
        expected_files = [f"{id}_part_{i}.wav" for i in range(1, len(contents) + 1)]
        actual_files = [f for f in expected_files if (audio_dir / f).exists()]

        # Nếu thiếu file, retry tạo audio cho đoạn thiếu (chỉ 1 lần)
        missing_indices = [i+1 for i, f in enumerate(expected_files) if not (audio_dir / f).exists()]
        if missing_indices:
            logging.warning(f"[AUDIO] Missing {len(missing_indices)} audio files. Retrying...")
            retry_threads = []
            for i in missing_indices:
                content = contents[i-1]
                proxy = None
                proxies_retry = PROXY_URL.copy()
                random.shuffle(proxies_retry)
                while proxies_retry:
                    candidate = proxies_retry[i % len(proxies_retry)]
                    if AudioService.is_proxy_alive(candidate):
                        proxy = candidate
                        break
                    else:
                        logging.warning(f"[AUDIO] Removed error proxy (retry): {candidate}")
                        proxies_retry.remove(candidate)
                if not proxy:
                    logging.error("[AUDIO] No working proxies available for retry. Abort.")
                    continue
                api_key = api_keys[i % len(api_keys)]['key']
                key_name = api_keys[i % len(api_keys)]['name']
                delay = round(len(content) * 0.07, 2)
                logging.info(f"[AUDIO] Retrying part {i} | Len={len(content)} | Delay={delay}s")
                t = threading.Thread(
                    target=AudioService.process_ggai_studio,
                    args=(content, audio_dir, id, i, api_key, proxy, delay)
                )
                t.start()
                retry_threads.append((t, delay, i))
                usage_log[key_name] = usage_log.get(key_name, 0) + 1
            # Đợi các thread retry hoàn thành
            for t, delay, _ in retry_threads:
                t.join(timeout=delay + 5)
            # Kiểm tra lại lần cuối
            actual_files = [f for f in expected_files if (audio_dir / f).exists()]
            if len(actual_files) < len(contents):
                missing_files = [expected_files[i-1] for i in missing_indices if not (audio_dir / expected_files[i-1]).exists()]
                logging.error(f"[AUDIO] Still missing {len(contents) - len(actual_files)} audio files after retry. Abort merge.")
                logging.error(f"[AUDIO] Missing files after retry: {missing_files}")
                logging.error(f"[AUDIO] You can manually generate audio for these parts using the file: {content_json_path}")
                return None

        # Chỉ merge khi đã đủ số lượng file audio
        file_list = [f for f in expected_files if (audio_dir / f).exists()]
        if len(file_list) < len(contents):
            missing_files = [expected_files[i-1] for i in missing_indices if not (audio_dir / expected_files[i-1]).exists()]
            logging.error("[AUDIO] Not enough audio files to merge. Abort.")
            logging.error(f"[AUDIO] Missing files: {missing_files}")
            logging.error(f"[AUDIO] You can manually generate audio for these parts using the file: {content_json_path}")
            return None

        merged_path = Path(MergeAudio.merge(audio_dir, file_list, id=id))
        logging.info(f"[AUDIO] Created audio successfully: {merged_path}")

        # Upload lên Google Drive ngay sau khi merge
        try:
            folder_id = os.environ.get("GDRIVE_FOLDER_ID", "n8n audio")  # Set your Google Drive folder ID if needed
            uploaded = UploadToDrive.upload_audio(merged_path, folder_id=folder_id)
            logging.info(f"[DRIVE] Uploaded file: https://drive.google.com/file/d/{uploaded.get('id')}/view")
        except Exception as e:
            logging.warning(f"[DRIVE] Upload failed: {e}")

        # Ghi log usage
        try:
            log_file_path = Path(DATA_TEMP) / "api_key_usage_log.json"
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(resource_path(log_file_path), "w", encoding="utf-8") as f:
                json.dump({"date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "usage": usage_log}, f, indent=2)
        except Exception as log_err:
            logging.warning(f"[AUDIO] Failed to write usage log: {log_err}")
        return merged_path.resolve()

if __name__ == "__main__":
    
    # temp_files = [f"10013_part_{i}.wav" for i in range(1, 66)]
    # audio_dir = "D:/Tan.n-AIEngineer/Program/Video-render-order-theta/app/database/Audio"
    # merged_path = MergeAudio.merge(audio_dir, temp_files, id=10013)
    # print("Merged path:", merged_path)
    audio_dir = resource_path(r"E:\python\Video-render-order-theta\app\database\Audio\None")
    id = 10016
    idx = 12
    merged_path = MergeAudio.merge(audio_dir, [f"{id}_part_{i}.wav" for i in range(1, idx)], id=id)