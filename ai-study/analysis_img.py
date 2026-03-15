from openai import OpenAI
import base64
import streamlit as st


# 이미지 인코딩 함수 정의
def encode_image(image_path):
    return base64.b64encode(image_path.read()).decode("utf-8")


# 이미지 분석 함수 정의
def analyze_image(prompt, base64_image, client):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        # 이미지 분석 요청 프롬프트
                        "type": "text",
                        "text": prompt,
                    },
                    {
                        # base64로 변환된 이미지 데이터
                        "type": "image_url",
                        ""
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
    )
    return response.choices[0].message.content


def main():
    st.set_page_config(layout="wide")
    st.title("이미지 분석 프로그램")
    st.caption("이미지를 업로드하면 분석 결과가 출력됩니다.")

    with st.sidebar:
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        st.write("[OpenAI API Key 받기](https://platform.openai.com/account/api-keys)")

    # 파일 업로드 위젯 구현
    image_file = st.file_uploader(
        "이미지를 업로드하세요.", type=["jpg", "jpeg", "png"], label_visibility="hidden"
    )

    if st.button("이미지 분석"):
        if not openai_api_key:
            st.error("OpenAI API Key를 입력해주세요.")
            st.stop()
        if not image_file:
            st.error("이미지를 업로드해주세요.")
            st.stop()

        client = OpenAI(api_key=openai_api_key)
        with st.spinner("이미지 분석 중..."):
            base64_image = encode_image(image_file)
            prompt = f"""
            너는 최고의 데이터 분석가야.
            - 데이터를 분석해 핵심 내용을 정리한 표와 그에 관한 인사이트를 보여줘.
            - 표는 마크다운으로 만들어.
            - 최소한 두 가지 이상의 인사이트를 제시해.
            - 분석 결과만 응답해.
            """
            result = analyze_image(prompt, base64_image, client)
            st.write(result)


if __name__ == "__main__":
    main()
