import streamlit as st
import pymupdf
from openai import OpenAI


# pdf 불러오기 및 텍스트 추출 함수
def get_text_from_pdf(pdf_data, page_number):
    document = pymupdf.open(stream=pdf_data, filetype="pdf")  # pdf 파일 열기
    page = document[page_number - 1]  # 페이지 가져오기
    return page.get_text()  # 텍스트 추출 반환


def convert_pdf_to_images(pdf_data):
    document = pymupdf.open(stream=pdf_data, filetype="pdf")  # pdf 파일 열기

    images = []

    for page_num in range(len(document)):
        page = document[page_num]
        pix = page.get_pixmap(dpi=150)  # 페이지를 이미지로 변환
        img_path = f"page_{page_num + 1}.png"  # 이미지 저장경로 설정
        pix.save(img_path)
        images.append(img_path)

    return images


def main():
    st.set_page_config(layout="wide")
    with st.sidebar:
        st.title("PDF 번역/요약 프로그램")
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        st.write("[OpenAI API Key 받기](https://platform.openai.com/account/api-keys)")

        pdf_file = st.file_uploader("PDF 파일을 업로드하세요", type=["pdf"])

        # 주요 세션 상태 초깃값 설정
        if "images" not in st.session_state:
            st.session_state.images = []
        if "page_number" not in st.session_state:
            st.session_state.page_number = 1
        client = None
        # OpenAI 클라이언트 생성
        if openai_api_key:
            client = OpenAI(api_key=openai_api_key)

        # 문서 번역/요약 함수 정의
        def process_text(prompt, text):
            content = prompt + "\n" + text
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": content}],
            )
            return response.choices[0].message.content

        # pdf 파일이 업로드된 경우의 조건부 로직
        if pdf_file:
            # 메모리에 PDF 내용 저장
            pdf_data = pdf_file.read()
            # PDF 페이지를 이미지로 변환해서 세션에 저장
            st.session_state.images = convert_pdf_to_images(pdf_data)
            total_pages = len(st.session_state.images)
            # 페이지 번호 입력 위젯
            st.session_state.page_number = st.number_input(
                "페이지 번호를 입력하세요",
                min_value=1,
                max_value=total_pages,
                value=1,
            )

    if pdf_file:
        # 열 레이아웃 설정
        left_col, right_col = st.columns([1, 1])
        # 왼쪽 열: 페이지 이미지 표시
        with left_col:
            st.subheader("미리보기")
            st.image(
                st.session_state.images[st.session_state.page_number - 1],
                caption=f"Page {st.session_state.page_number}",
                width="stretch",
            )
        # 오른쪽 열: 페이지 텍스트 출력
        with right_col:
            st.subheader("PDF 요약")
            pdf_text = get_text_from_pdf(pdf_data, st.session_state.page_number)

            # 프롬프트 입력 위젯 생성
            start_prompt = """다음 문서를 개조식으로 요약하되 한글로 번역해주세요.
- ~음, ~했음 등의 어조를 사용하세요.
- 가장 중요한 내용을 중심으로 간결하게 요약하세요.
- 마크다운을 이용해 구조화된 요약 결과를 보여주세요.
"""

            prompt = st.text_area("프롬프트 입력:", height=120, value=start_prompt)
            # 요약 버튼 및 결과 표시
            if st.button("요약"):
                if client is None:
                    st.error("유효한 API Key를 입력하세요.")
                elif not pdf_text.strip():
                    st.error("문서를 입력하세요.")
                else:
                    with st.spinner("요약 중..."):
                        try:
                            result = process_text(prompt, pdf_text)
                            st.subheader("요약 결과")
                            st.write(result)
                        except Exception as e:
                            st.error(f"요약 중 오류 발생: {e}")


if __name__ == "__main__":
    main()


# pdf_data = "sample.pdf"
# page_number = 1

# pdf_text = get_text_from_pdf(pdf_data, page_number)
# print(pdf_text)

# convert_pdf_to_images(pdf_data)
