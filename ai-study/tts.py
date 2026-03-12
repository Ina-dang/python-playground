from openai import OpenAI
from dotenv import load_dotenv
import streamlit as st

# load_dotenv()

# client = OpenAI()


def text_to_speech(client, text):
    response = client.audio.speech.create(model="tts-1", voice="shimmer", input=text)

    # 음성파일 경로 설정
    speech_file_path = "AI음성.mp3"

    # 음성 파일 저장
    with open(speech_file_path, "wb") as audio_file:
        audio_file.write(response.content)


def main():
    st.set_page_config(layout="wide")
    st.title("AI 텍스트 낭독기")
    st.caption("텍스트를 음성으로 변환하기")

    with st.sidebar:
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        st.write("[OpenAI API Key 받기](https://platform.openai.com/account/api-keys)")

    default_user_input = """안녕하세요. 여러분.
    OpenAI를 활용한 음성 변환 프로그램 입니다.
    텍스트를 입력하고 음성을 들어보세요.
  """

    user_input = st.text_area(
        "음성으로 변환할 텍스트를 입력하세요.", value=default_user_input, height=300
    )

    # 음성 생성 버튼 추가
    if st.button("음성 생성"):
        if not openai_api_key:
            st.info("계속하려면 API Key를 입력하세요.")
            st.stop()

        if not user_input.strip():
            st.warning("음성으로 변환할 텍스트를 입력하세요.")
            st.stop()

        # OpenAI 클라이언트 생성
        client = OpenAI(api_key=openai_api_key)

        # 텍스트 - 음성 변환 함수 호출
        text_to_speech(client, user_input)

        # 음성 파일을 오디오 위젯으로 출력
        with open("AI음성.mp3", "rb") as audio_file:
            audio_data = audio_file.read()
            st.audio(data=audio_data, format="audio/mpeg")


if __name__ == "__main__":
    main()

# text_to_speech(
#     "안녕하세요, OpenAI의 TTS 모델을 사용하여 텍스트를 음성으로 변환하는 예시입니다."
# )
