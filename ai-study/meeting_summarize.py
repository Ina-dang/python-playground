from openai import OpenAI
import streamlit as st


# 화자 추정 기반 대화 정리 함수
def format_transcription_by_speaker(text, client):
    prompt = f"""
다음은 회의에서 녹음된 텍스트입니다.
화자를 정확히 식별할 수 없다는 점을 감안해서, 문맥을 바탕으로 화자를 추정해 대화를 정리해주세요.

조건:
- 반드시 `참가자1: 내용` 또는 `참가자2: 내용` 형식으로만 작성할 것
- 필요하면 `참가자3` 이상도 사용할 수 있음
- 한 줄에 한 화자 발화만 작성할 것
- 불필요한 설명, 주석, 서론은 쓰지 말 것
- 문장이 너무 길면 자연스럽게 나눌 것
- 원문 내용을 최대한 유지할 것

원문:
{text}
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


# 텍스트 요약 함수
def summarize_text(text, client):
    prompt = f"다음은 회의에서 녹음된 텍스트 입니다. 이 텍스트를 간결하게 마크다운으로 요약해주세요.\n\n{text}"
    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


def main():
    st.set_page_config(layout="wide")
    st.title("회의록 요약 프로그램")
    st.caption("회의를 녹음한 음성파일을 업로드하면 원본 텍스트와 요약본을 출력합니다.")
    with st.sidebar:
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        st.write("[OpenAI API Key 받기](https://platform.openai.com/account/api-keys)")

    if "message" not in st.session_state:
        st.session_state.messages = []

    # 파일 업로드 위젯 생성
    mp3_file = st.file_uploader("mp3 파일을 업로드하세요.", type=["mp3"])
    if st.button("음성-텍스트 변환"):
        if not openai_api_key:
            st.error("OpenAI API Key를 입력해주세요.")
            st.stop()
        if not mp3_file:
            st.error("mp3 파일을 업로드해주세요.")
            st.stop()

        client = OpenAI(api_key=openai_api_key)
        with st.spinner("음성-텍스트 변환 중..."):
            transcription = client.audio.transcriptions.create(
                model="whisper-1", file=mp3_file, response_format="text"
            )
            speaker_text = format_transcription_by_speaker(transcription, client)
            summary_text = summarize_text(transcription, client)

            # 두개의 탭 생성 및 결과 출력
            tab1, tab2 = st.tabs(["원본텍스트", "요약본"])
            with tab1:
                st.write(speaker_text)
            with tab2:
                st.write(summary_text)


if __name__ == "__main__":
    main()
