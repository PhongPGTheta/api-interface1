import os
import json
import random
import requests
from datetime import datetime
from pathlib import Path
import time
import logging
from contextlib import contextmanager
from core.elevenlabs import ELEVENLABS_ACCOUNTS, HISTORY_VOICE_ID_PATH

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)
logger = logging.getLogger(__name__)

class AccountManager:
    ELEVENLABS_ACCOUNTS = ELEVENLABS_ACCOUNTS
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
            'Accept-Language': accept_language,
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Origin': 'https://elevenlabs.io',
            'Referer': 'https://elevenlabs.io/',
            'xi-api-key': api_key
        }
        return headers

    @staticmethod
    def add_random_delay(min_delay=5.0, max_delay=10.0):
        time.sleep(random.uniform(min_delay, max_delay))

    @staticmethod
    @contextmanager
    def temporary_proxy(proxy_url):
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


# =========================
# credit Management
# =========================
class CreditManager:
    AUDIO_TEMP_DIR = Path("database/AudioTemp")
    AUDIO_TEMP_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def get_temp_file_path():
        now = datetime.now()
        return CreditManager.AUDIO_TEMP_DIR / f"{now.month}_{now.year}_temp.json"

    @staticmethod
    def load_accounts_temp():
        path = CreditManager.get_temp_file_path()
        if not path.exists():
            accounts = [dict(acc, credit=10000, lastupdate=datetime.now().isoformat()) for acc in AccountManager.ELEVENLABS_ACCOUNTS]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(accounts, f, ensure_ascii=False, indent=2)
            return accounts
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def save_accounts_temp(accounts):
        path = CreditManager.get_temp_file_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(accounts, f, ensure_ascii=False, indent=2)

    @staticmethod
    def get_random_elevenlabs_account(min_credit=10):
        accounts = CreditManager.load_accounts_temp()
        available = [acc for acc in accounts if acc.get("credit", 0) > min_credit]
        if not available:
            return None
        return random.choice(available)

    @staticmethod
    def update_elevenlabs_account(api_key, used_credit):
        accounts = CreditManager.load_accounts_temp()
        for acc in accounts:
            if acc["api_key"] == api_key:
                acc["credit"] = max(0, acc.get("credit", 0) - used_credit)
                acc["lastupdate"] = datetime.now().isoformat()
                break
        CreditManager.save_accounts_temp(accounts)

# =========================
# ElevenLabs API Logic
# =========================
class ElevenLabsAPI:
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
                save_path = Path(HISTORY_VOICE_ID_PATH)
            else:
                save_path = Path(save_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump({"voice_ids": voice_ids}, f, ensure_ascii=False, indent=2)
            logger.info(f"Fetched and saved {len(voice_ids)} voice_ids.")
            return voice_ids
        else:
            logger.error(f"Failed to fetch voices: {resp.status_code} {resp.text}")
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
            with open(output_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"Saved TTS audio to {output_path}")
            return output_path
        else:
            logger.error(f"TTS failed: {resp.status_code} {resp.text}")
            raise Exception(f"TTS failed: {resp.status_code} {resp.text}")

    @staticmethod
    def split_script_by_word_limit(text, max_words=500):
        words = text.split()
        segments = []
        i = 0
        while i < len(words):
            end = min(i + max_words, len(words))
            segments.append(" ".join(words[i:end]))
            i = end
        return segments

    @staticmethod
    def is_credit_valid(api_key, proxy_url=None) -> bool:
        """
        Kiểm tra credit có hợp lệ hay không bằng cách gọi /v1/voices
        """
        try:
            url = "https://api.elevenlabs.io/v1/user"
            headers = AccountManager.get_random_headers(api_key)
            with AccountManager.temporary_proxy(proxy_url):
                resp = requests.get(url, headers=headers, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"[credit CHECK] credit invalid or failed: {e}")
            return False

# =========================
# Audio Processing Service
# =========================
class AudioService:
    @staticmethod
    def split_script_by_word_limit(text, max_words=500):
        words = text.strip().split()
        return [" ".join(words[i:i+max_words]) for i in range(0, len(words), max_words)]

    @staticmethod
    def extract_account_name(api_key):
        return api_key[-6:]

    @staticmethod
    def update_credit_from_error(e, api_key):
        try:
            if 'quota_exceeded' in str(e):
                import re
                match = re.search(r'You have (\d+) credits.*?while (\d+) credits', str(e))
                if match:
                    left, required = int(match.group(1)), int(match.group(2))
                    used = required - left + 1
                    CreditManager.update_elevenlabs_account(api_key, used)
        except:
            pass

    @staticmethod
    def process_audio_service(transcript, audio_dir, id=""):
        if not transcript:
            logger.error("Transcript is empty!")
            raise ValueError("Transcript is empty!")

        segments = AudioService.split_script_by_word_limit(transcript, max_words=500)
        total_segments = len(segments)
        logger.info(f"Split transcript into {total_segments} segment(s)")

        audio_dir = Path(audio_dir)
        audio_dir.mkdir(parents=True, exist_ok=True)
        temp_files = []

        account = CreditManager.get_random_elevenlabs_account(min_credit=10)
        if not account:
            raise Exception("No ElevenLabs account available.")

        api_key = account['api_key']
        proxy_url = account.get('proxy_url', '')
        account_name = AudioService.extract_account_name(api_key)

        voice_ids = ElevenLabsAPI.fetch_and_save_all_voice_ids(api_key, proxy_url)
        if not voice_ids:
            raise Exception("No voice ID fetched.")
        voice_id = random.choice(voice_ids)

        for idx, seg in enumerate(segments):
            completed = idx + 1
            percent = int(completed * 100 / total_segments)
            success = False

            while not success:
                try:
                    temp_path = str(audio_dir / f"{id}_temp_{completed}.mp3")
                    ElevenLabsAPI.convert_tts(seg, api_key, proxy_url, voice_id, temp_path)
                    temp_files.append(temp_path)
                    CreditManager.update_elevenlabs_account(api_key, len(seg))
                    logger.info(f"Processed segment {completed}/{total_segments} ({percent}%) using account: {account_name}")
                    success = True
                except Exception as e:
                    AudioService.update_credit_from_error(e, api_key)
                    logger.warning(f"Switching account due to error: {str(e)}")
                    account = CreditManager.get_random_elevenlabs_account(min_credit=10)
                    if not account:
                        raise Exception("No valid ElevenLabs account available after error.")
                    api_key = account['api_key']
                    proxy_url = account.get('proxy_url', '')
                    account_name = AudioService.extract_account_name(api_key)

        merged_file = str(audio_dir / f"{id}.mp3")
        silence_1s = audio_dir / "silence1s.mp3"
        filelist_path = audio_dir / f"{id}_filelist.txt"

        # Đường dẫn đến ffmpeg (tương đối)
        ffmpeg_path = str(Path("app/bin/ffmpeg.exe").resolve())

        # Tạo silence1s.mp3 nếu chưa có
        if not silence_1s.exists():
            os.system(f'"{ffmpeg_path}" -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 -t 1 -q:a 9 -acodec libmp3lame "{silence_1s}"')

        # Ghi danh sách file cần ghép
        with open(filelist_path, "w", encoding="utf-8") as f:
            f.write(f"file '{silence_1s.resolve()}'\n")
            for temp in temp_files:
                f.write(f"file '{Path(temp).resolve()}'\n")
            f.write(f"file '{silence_1s.resolve()}'\n")

        # Ghép audio bằng ffmpeg
        os.system(f'"{ffmpeg_path}" -f concat -safe 0 -i "{filelist_path}" -c copy "{merged_file}"')

        # Xoá danh sách tạm
        os.remove(filelist_path)

        logger.info(f"Final audio saved to {merged_file}")
        return merged_file
    
    
# =========================
# Example Usage
# =========================
if __name__ == "__main__":
    transcript = "Xin chào, đây là ví dụ chuyển đổi văn bản thành giọng nói bằng ElevenLabs API."
    history_path = Path(HISTORY_VOICE_ID_PATH)
    audio_dir = Path("database/Audio")
    if history_path.exists():
        with open(history_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            voice_ids = data.get("voice_ids", [])
    else:
        voice_ids = []
    if voice_ids:
        random_voice_id = random.choice(voice_ids)
        account = AccountManager.ELEVENLABS_ACCOUNTS[0]
        audio_dir.mkdir(parents=True, exist_ok=True)
        output_filename = f"test_random_voice.mp3"
        output_path = str(audio_dir / output_filename)
        ElevenLabsAPI.convert_tts(transcript, account["api_key"], account.get("proxy_url", ""), random_voice_id, output_path)
        logger.info(f"Audio (random voice) saved at: {output_path}")
    else:
        audio_path = AudioService.process_audio_service(transcript, audio_dir, id="1")
        logger.info(f"Audio saved at: {audio_path}")
