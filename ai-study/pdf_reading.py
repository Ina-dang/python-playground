import streamlit as st
import pymupdf


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
            st.subheader("텍스트 추출")
            pdf_text = get_text_from_pdf(pdf_data, st.session_state.page_number)
            st.write(pdf_text)


if __name__ == "__main__":
    main()


# pdf_data = "sample.pdf"
# page_number = 1

# pdf_text = get_text_from_pdf(pdf_data, page_number)
# print(pdf_text)

# convert_pdf_to_images(pdf_data)
