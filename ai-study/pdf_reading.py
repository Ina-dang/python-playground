import pymupdf


# pdf 불러오기 및 텍스트 추출 함수
def get_text_from_pdf(pdf_data, page_number):
    document = pymupdf.open(pdf_data)  # pdf 파일 열기
    page = document[page_number - 1]  # 페이지 가져오기
    return page.get_text()  # 텍스트 추출 반환


def convert_pdf_to_images(pdf_data):
    document = pymupdf.open(pdf_data)

    images = []

    for page_num in range(len(document)):
        page = document[page_num]
        pix = page.get_pixmap(dpi=150)  # 페이지를 이미지로 변환
        img_path = f"page_{page_num + 1}.png"  # 이미지 저장경로 설정
        pix.save(img_path)
        images.append(img_path)

    return images


pdf_data = "sample.pdf"
page_number = 1

pdf_text = get_text_from_pdf(pdf_data, page_number)
print(pdf_text)

convert_pdf_to_images(pdf_data)
