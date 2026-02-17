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

    # 프롬프트 추가
    system_message = """
  너의 이름은 친구봇이야.
  너는 항상 반말을 하는 챗봇이니까 절대로 다나까 같은 높임말을 사용해선 안돼
  항상 반말로 친절하게 친근하게 대답해줘.
  영어로 질문을 받아도 답변은 무조건 한글로 하고.
  한글이 아닌 답변을 하게되면 다시 생각해서 답변을 꼭 한글로 만들어.
  모든 답변 끝에는 답변에 맞는 이모지를 추가해.
"""

    # 대화 내용 관리를 위한 세션 상태 설정
    state = st.session_state
    if "messages" not in state:
        state.messages = [{"role": "system", "content": system_message}]

    # 기존 대화 내역 표시
    index = 0
    for message in state.messages:
        if index > 0:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        index = index + 1

    # OpenAI 클라이언트 생성
    client = OpenAI(api_key=openai_api_key)

    # 입력 대화창 구성
    user_input = st.chat_input("무엇이 궁금한가요?")
    if user_input:
        state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.write(user_input)
        with st.chat_message("assistant"):
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=state.messages,
                stream=True,
            )
            response = st.write_stream(stream)
        state.messages.append({"role": "assistant", "content": response})


# main 함수 실행
if __name__ == "__main__":
    main()
