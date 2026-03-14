import streamlit as st
from openai import OpenAI


def main():
    st.set_page_config(layout="wide")
    st.title("보고서 작성 프로그램")
    client = None
    with st.sidebar:
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        st.write("[OpenAI API Key 받기](https://platform.openai.com/account/api-keys)")

        if openai_api_key:
            client = OpenAI(api_key=openai_api_key)

        # 보고서 작성 함수 정의
        def process_text(prompt, text):
            content = prompt + "\n" + text
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": content}],
            )
            return response.choices[0].message.content

    # 보고서 작성 프롬프트 입력
    prompt = """
      너는 보고서 작성 전문가야.
      다음 형식으로 보고서를 작성해줘.
      - 마크다운을 활용해 체계적으로 작성할 것
      - heading2(##) 3개, 각 heading2 내에서는 heading3(###) 2개로 구성할 것
      - heading2의 내용은 300자 이상으로 작성할 것
      - 목차는 제외할 것
      - 보고서 내용만 응답 결과로 보여줄 것
      """
    default_user_input = """생성형 AI가 세상을 어떻게 바꿀 수 있을까?"""
    user_input = st.text_area(
        "작성할 보고서의 주제 또는 내용을 입력하세요:",
        value=default_user_input,
        height=70,
    )

    # 보고서 작성
    if st.button("보고서 작성"):
        if client is None:
            st.error("유효한 API Key를 입력하세요.")
            st.stop()
        if not user_input.strip():
            st.warning("작성할 보고서의 주제를 입력하세요.")
            st.stop()
        with st.spinner("작성 중..."):
            result = process_text(prompt, user_input)
            st.write(result)


if __name__ == "__main__":
    main()
