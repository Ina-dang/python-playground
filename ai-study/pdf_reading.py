import pymupdf


def get_text_from_pdf(pdf_data, page_number):
    document = pymupdf.open(pdf_data)
    page = document[page_number - 1]
    return page.get_text()


pdf_data = "sample.pdf"
page_number = 1

pdf_text = get_text_from_pdf(pdf_data, page_number)
print(pdf_text)
