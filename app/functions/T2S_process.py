from core.config import GOOGLE_API_KEY, DATA_ORDER_CONTENT_PATH,\
      NUMBER_WORDS_OF_CONTENT, DATA_TEMP
from core.promptcontrol import PROMPTTRANS
from database.datacontrol import T2SModule
from schemas.rules import DataReturn
from pathlib import Path
from functions.get_transcript import GetTranscript
from datetime import datetime
import google.generativeai as genai
import logging
import re


class TextPrecheck:
    @staticmethod
    def clean_content(text: str) -> str:
        """Loại bỏ markdown, tiêu đề, ký hiệu đặc biệt, dấu ngoặc kép, dấu sao... nhưng giữ lại \n để phân biệt xuống dòng."""
        # Loại bỏ các tiêu đề phổ biến
        text = re.sub(r"(Content Summary:|Thematic Insights:|Story Inspiration Ideas:)", "", text, flags=re.IGNORECASE)
        # Loại bỏ markdown bold/italic (**text**, *text*, __text__, _text_)
        text = re.sub(r"(\*\*|__|\*|_)", "", text)
        # Loại bỏ dấu ngoặc kép đầu/cuối và các ký hiệu lạ
        text = text.replace('"', "")
        # Loại bỏ các ký hiệu đánh dấu đầu dòng phổ biến
        text = re.sub(r"^[-•\d.]+\s*", "", text, flags=re.MULTILINE)
        # Không loại bỏ \n, chỉ loại bỏ các dòng trống dư thừa (nhiều \n liên tiếp thành 1)
        text = re.sub(r"\n{2,}", "\n", text)
        # Loại bỏ khoảng trắng thừa nhưng giữ lại \n
        # Đầu tiên loại bỏ khoảng trắng ở đầu/cuối mỗi dòng
        text = '\n'.join([line.strip() for line in text.split('\n')])
        # Sau đó loại bỏ khoảng trắng thừa giữa các từ
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()
    
    @staticmethod
    def split_content_by_newline(text: str) -> list:
        """Tách nội dung thành các đoạn dựa trên dấu xuống dòng thực sự."""
        # Loại bỏ các khoảng trắng dư thừa đầu/cuối mỗi đoạn
        return [segment.strip() for segment in text.split('\n') if segment.strip()]
    
class TranscriptManager:
    @staticmethod
    def transcript_to_new_script(order_data: dict, uuid: str) -> str:
        try:
            logging.info(f"[TRANSCRIPT] Getting transcript for url={order_data.url}, language={getattr(order_data, 'language', 'en')}")
            transcript_path = GetTranscript(order_data.url, getattr(order_data, 'language', 'en'))
            transcript_file = transcript_path.get_transcript()
            logging.info(f"[TRANSCRIPT] Transcript file path: {transcript_file}")

            with open(transcript_file, "r", encoding="utf-8") as f:
                transcript = f.read()
            trans_words = [word for word in transcript.split() if word.strip()]
            logging.info(f"[TRANSCRIPT] Transcript loaded, length={len(trans_words)} words")

            passages = 1
            if len(trans_words) > 400:
                passages = len(trans_words) // 400
                logging.info(f"[Passage] Splitting content into passages of length {passages}")

            # --- Xử lý prompt: chỉ replace sau "Now I will provide the input:" ---
            split_token = "Now I will provide the input:"
            order_text = getattr(order_data, 'content_order', None)
            if split_token in PROMPTTRANS:
                desc, input_part = PROMPTTRANS.split(split_token, 1)
                input_part = input_part.replace("[Order]", order_text)\
                    .replace("[Passage]", str(passages))\
                    .replace("[Number_of_words]", str(NUMBER_WORDS_OF_CONTENT))\
                    .replace("[Language]", getattr(order_data, 'language', 'en'))\
                    .replace("[Transcript]", transcript)
                prompt = desc + split_token + input_part
            else:
                prompt = PROMPTTRANS.replace("[Order]", order_text)\
                    .replace("[Passage]", str(passages))\
                    .replace("[Number_of_words]", str(NUMBER_WORDS_OF_CONTENT))\
                    .replace("[Language]", getattr(order_data, 'language', 'en'))\
                    .replace("[Transcript]", transcript)
            logging.info(f"[GEMINI] Prompt prepared, length={len(prompt)}")

            with open(f"{DATA_TEMP}/prompt.txt", "w", encoding="utf-8") as f:
                f.write(prompt)

            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.5-flash")
            logging.info(f"[GEMINI] Sending order_data to Gemini API...")

            response = model.generate_content(prompt)
            content = response.text if hasattr(response, 'text') else str(response)
            content = TextPrecheck.clean_content(content)
            w_content = content.split()
            logging.info(f"[GEMINI] Gemini response received, content length={len(w_content)}")

            #data_trans = f"{DATA_ORDER_CONTENT_PATH}/{order_data.id}.txt"
            # Sử dụng uuid nếu id là None
            file_id = order_data.id if order_data.id is not None else uuid
            data_trans = f"{DATA_ORDER_CONTENT_PATH}/{file_id}.txt"
            # Lưu ra file txt, giữ nguyên \n
            with open(f"{data_trans}", "w", encoding="utf-8") as f:
                f.write(content)
            order_file = DataReturn.server_url(Path(data_trans))
            order_data.content_order = order_file
            order_data.length = len(w_content)
            order_data.status = "done"
            order_data.created_at = datetime.now().isoformat()
            logging.info(f"[ORDER] Content saved to {data_trans}")

            T2SModule.write_or_update_data(order_data.model_dump(), order_data.id)
            logging.info(f"[ORDER] Order data updated to status=done for uuid={uuid}, id={order_data.id}")
            
        except Exception as e:
            order_data.status = f"error: {e}"
            T2SModule.write_or_update_data(order_data.model_dump(), order_data.id)
            logging.error(f"[ERROR] Exception occurred for uuid={uuid}, id={order_data.id}: {e}")