import streamlit as st
from openai import OpenAI
from io import BytesIO
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn


# MS워드 문서 변환 함수 정의
def markdown_to_docx(markdown_content: str, font_name: str, base_font_size: int):
    doc = Document()
    lines = markdown_content.split("\n")

    for line in lines:
        line = line.strip()  # 양쪽 공백 제거
        if not line:
            continue  # 빈 줄은 건너뛰기
        if line.startswith("## "):
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(line[3:])  # '## ' 제거
            font = run.font  # 글꼴 설정
            font.size = Pt(base_font_size + 3)
            font.name = font_name
            font.bold = True
            run._element.rPr.rFonts.set(qn("w:eastAsta"), font_name)  # 한국어 설정
        elif line.startswith("### "):
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(line[4:])  # '### ' 제거
            font = run.font  # 글꼴 설정
            font.size = Pt(base_font_size + 1)
            font.name = font_name
            font.bold = True
            run._element.rPr.rFonts.set(qn("w:eastAsta"), font_name)  # 한국어 설정
        else:
            paragraph = doc.add_paragraph()
            run = paragraph.add_run(line)  # 일반 텍스트
            font = run.font  # 글꼴 설정
            font.size = Pt(base_font_size)
            font.name = font_name
            run._element.rPr.rFonts.set(qn("w:eastAsta"), font_name)  # 한국어 설정

    # 문서 객체를 바이트 데이터로 변환
    byte_io = BytesIO()  # 메모리상에서 바이트 데이터를 저장할 객체 생성
    doc.save(byte_io)  # MS워드 문서를 byte_io 객체에 저장
    byte_io.seek(0)  # byte_io 객체의 포인터를 처음으로 이동
    return byte_io  # 바이트 데이터 반환


def main():
    st.set_page_config(layout="wide")
    st.title("보고서 작성 프로그램")
    client = None
    with st.sidebar:
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        st.write("[OpenAI API Key 받기](https://platform.openai.com/account/api-keys)")

        # 폰트 종류 및 크기 선택 위젯 추가
        font_name = st.selectbox("글꼴 선택", ["맑은 고딕", "나눔고딕", "바탕체"])
        base_font_size = st.slider(
            "기본 글꼴 크기", min_value=8, max_value=24, value=11
        )

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

            # MS워드 문서 변환 함수 호출
            docx_file = markdown_to_docx(result, font_name, base_font_size)

            # 다운로드 버튼 생성
            st.download_button(
                label="보고서 다운로드", data=docx_file, file_name="보고서.docx"
            )


if __name__ == "__main__":
    main()
