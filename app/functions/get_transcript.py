import logging
import yt_dlp
import requests
from core.config import DATA_TRANSCRIPT_PATH
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)
class GetTranscript:
    def __init__(self, video_url: str, language_code: str = "vi"):
        self.video_url = video_url
        self.language_code = language_code

    def ProcessURL(self, url: str) -> str:
        """
        Trích xuất ID video từ URL YouTube.

        :param url: URL của video YouTube.
        :return: ID video.
        """
        if "youtu.be" in url:
            return url.split("/")[-1]
        elif "youtube.com/watch?v=" in url:
            return url.split("v=")[-1].split("&")[0]
        else:
            raise ValueError("Invalid YouTube URL format")

    def yt_dlp_process(self) -> str:
        ydl_opts = {
            'skip_download': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'quiet': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(self.video_url, download=False)
                if 'automatic_captions' in info and 'en' in info['automatic_captions']:
                    return info['automatic_captions']['en'][0]['url']
                else:
                    return "No transcript available."
            except Exception as e:
                return f"Error retrieving transcript: {str(e)}"


    def tactip_process(self, url, language_code="vi") -> str:
        """
        Gửi yêu cầu đến TactiP API để lấy transcript từ video YouTube.

        :param video_url: URL của video YouTube.
        :param language_code: Mã ngôn ngữ transcript mong muốn (mặc định là "en").
        :return: Dữ liệu JSON chứa transcript nếu thành công, hoặc thông tin lỗi.
        """
        api_url = "https://tactiq-apps-prod.tactiq.io/transcript"

        headers = {
            "accept": "*/*",
            "accept-language": "vi,en-US;q=0.9,en;q=0.8",
            "content-type": "application/json",
            "origin": "https://tactiq.io",
            "referer": "https://tactiq.io/",
            "user-agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
            ),
            "sec-ch-ua": '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "priority": "u=1, i"
        }

        payload = {
            "videoUrl": url,
            "langCode": language_code
        }

        try:
            response = requests.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Không thể lấy transcript: {e}")
            return {}

    def get_transcript(self) -> str:
        raww_transcript = self.tactip_process(self.video_url, self.language_code)
        if not raww_transcript or "captions" not in raww_transcript:
            return "No transcript available."

        # print(f"[TactiP] Transcript retrieved successfully: {raww_transcript}")

        IDVideo = self.ProcessURL(self.video_url)
        with open(f"{DATA_TRANSCRIPT_PATH}/{IDVideo}.txt", "w", encoding="utf-8") as f:
            for caption in raww_transcript["captions"]:
                text = caption.get("text", "").strip()
                if text:
                    f.write(f"{text} ")
        return f"{DATA_TRANSCRIPT_PATH}/{IDVideo}.txt" # 


if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=y3ErOyiu_xs"  # Thay thế bằng URL video thực tế
    language_code = "en"  # Mã ngôn ngữ mong muốn

    transcript_fetcher = GetTranscript(video_url, language_code)
    transcript = transcript_fetcher.get_transcript()
    print(transcript)