from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

# 음성파일 경로 설정
speech_file_path = "AI음성.mp3"

response = client.audio.speech.create(
    model="tts-1", voice="sage", input="파이썬의 세계에 오신것을 환영합니다~!"
)

# 음성 파일 저장
with open(speech_file_path, "wb") as audio_file:
    audio_file.write(response.content)
