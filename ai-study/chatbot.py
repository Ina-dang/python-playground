import streamlit as st
from openai import OpenAI


# main 함수 선언
def main():
    # 메인 화면 구성
    st.set_page_config(layout="wide")
    st.title("친근한 AI 챗봇")
    st.caption("스트림릿과 OpenAI API를 활용한 간단 챗봇")

    # 사이드바 구성
    with st.sidebar:
        st.subheader("OpenAI API key 설정")
        openai_api_key = st.text_input("OpenAI API key", type="password")
        st.write("[OpenAI API Key 받기](https://platform.openai.com/account/api-keys)")

    # OpenAI 클라이언트 생성
    client = OpenAI(api_key=openai_api_key)

    # 입력 대화창 구성
    user_input = st.chat_input("무엇이 궁금한가요?")
    if user_input:
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "assistant", "content": user_input}],
                stream=True,
            )
            st.write(response)


# main 함수 실행
if __name__ == "__main__":
    main()
