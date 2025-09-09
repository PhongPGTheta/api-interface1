from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import time
import wave
from datetime import datetime
from pathlib import Path
from google.genai import Client, types

def createimage():
  client = genai.Client(api_key="AIzaSyAJA-lDE0ZfzRm8SKywdzQK4n2IGaYiKUU")

  contents = ('Wide shot of A young boy and his father tending sheep in a misty valley.. Time and setting: Bulgarian village, dawn, early 16th century. The image expresses a mood of serenity, depicted through facial expression, body posture, and environmental detail. Include period-accurate background elements such as buildings, terrain, clothing, and weather. Use the visual style: 16th-century Eastern European folk art. This style must be applied consistently across the entire scene. Do not include any modern visual elements or stylistic deviation. Color palette must follow: soft blues, greens, and grays with hints of dawn pink, ensuring tonal balance and historical accuracy. Image format must be 16:9 with all characters safely framed. Text, captions, or overlays are strictly excluded.')

  response = client.models.generate_content(
      model="gemini-2.0-flash-preview-image-generation",
      contents=contents,
      config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
      )
  )

  for part in response.candidates[0].content.parts:
    if part.text is not None:
      print(part.text)
    elif part.inline_data is not None:
      image = Image.open(BytesIO((part.inline_data.data)))
      image.save('gemini-native-image.png')
      image.show()

class GemTTS:
    @staticmethod
    def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
        with wave.open(filename, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(sample_width)
            wf.setframerate(rate)
            wf.writeframes(pcm)

    @staticmethod
    def createaudio(file_dir: str, content: str, api_key: str, id: int, idx: int):
        output_dir = Path(file_dir) / str(id)
        output_dir.mkdir(parents=True, exist_ok=True)

        file_path = output_dir / f"{id}_part_{idx}.wav"

        client = Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=content,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name='Orus',
                        )
                    )
                ),
            )
        )

        data = response.candidates[0].content.parts[0].inline_data.data
        GemTTS.wave_file(str(file_path), data)
        time.sleep(10)
        return file_path

if __name__ == "__main__":
    content = """The palace’s hidden structure of exploitation was both complex and deeply manipulative, governed by unwritten rules shaped over generations. Beneath its glittering exterior lay a system designed not just to educate, but to control—where vulnerability was routinely taken advantage of and power was measured not solely by rank, but by the ability to dominate those below. Eunuchs, who had once been victims themselves and bore the marks of past trauma, held considerable influence within this system. Tragically, many chose not to shield the new arrivals, but instead became enforcers of the very abuses they had once endured. Older students, in turn, often adopted the same behavior, targeting those beneath them as a means of survival and status. It became a twisted rite of passage: to ascend, one had to replicate the cruelty that had once been inflicted upon them. Palace officials, protected by status and hierarchy, took full advantage of the silence that pervaded the institution. They showed favor to the boys who fit their preferences—those who were compliant, pleasing, and easily shaped. These preferences were never openly discussed, but understood by all. Advancement was often granted not on merit, but on silent, unspoken compliance. What made this system so insidious was how fully it was woven into daily life. These exploitative dynamics weren’t whispered scandals—they were embedded into the very rhythm of the institution, treated as normal, even expected. Boys who received the attention of powerful patrons often found their lives easier, their privileges multiplying. Those who resisted were quietly pushed aside, given the worst duties, or simply vanished from the records. In such a world, silence was survival—and suffering, a hidden cost of ambition.
    """.strip()

    start = datetime.now()
    file = GemTTS.createaudio("database", content, api_key="AIzaSyAJA-lDE0ZfzRm8SKywdzQK4n2IGaYiKUU", id=10016, idx=8)
    end = datetime.now()

    print("Saved:", file)
    print("Length:", len(content.strip()))
    print("Time:", round((end - start).total_seconds(), 2), "s")
    print("Suggested Delay:", round(min(6 + len(content) * 0.01, 20), 2), "s")
