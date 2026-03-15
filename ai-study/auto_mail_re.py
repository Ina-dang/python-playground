from email.header import decode_header
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import imaplib
import email
import os

from openai import OpenAI
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv


load_dotenv()


# 메일 수신 함수 정의
def fetch_emails(email_id: str, email_password: str) -> pd.DataFrame:
    try:
        mail = imaplib.IMAP4_SSL("imap.naver.com")
        mail.login(email_id, email_password)

        # 수신 메일함 선택
        mail.select("inbox")
        result, data = mail.search(None, "ALL")

        # 최근 메일 열 개 가져오기
        mail_ids = data[0].split()[-10:]
        fetched_emails = []
        for mail_id in mail_ids:
            result, data = mail.fetch(mail_id, "(RFC822)")
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # 딕셔너리 선언 (메일 발신인/제목 디코딩, 메일 본문 가져오기)
            email_data = {
                "날짜": msg.get("Date"),
                "발신인": decode_mime_words(msg.get("From")),
                "제목": decode_mime_words(msg.get("Subject")),
                "본문": get_email_content(msg),
                "메일 객체": msg,
            }
            fetched_emails.append(email_data)
        fetched_emails.reverse()

        # 결과 리스트를 데이터프레임으로 변환
        df = pd.DataFrame(fetched_emails)
        return df
    except Exception as e:
        print(f"오류 발생: {e}")
        return None


# 메일 발신인/제목 디코딩 함수 정의
def decode_mime_words(encoded_string):
    if encoded_string is None:
        return ""
    decode_words = decode_header(encoded_string)
    decoded_string = ""
    for content, charset in decode_words:
        if isinstance(content, bytes):
            try:
                decoded_string += content.decode(charset or "utf-8")
            except:
                decoded_string += content.decode("latin1", errors="ignore")
        else:
            decoded_string += content

    return decoded_string


# 메일 본문 가져오기 함수 정의
def get_email_content(message):
    if message.is_multipart():
        parts = [
            get_email_content(part)
            for part in message.get_payload()
            if part.get_content_type() == "text/plain"
        ]
        return "\n".join(parts) if parts else ""
    else:
        content_type = message.get_content_type()
        if content_type == "text/plain":
            content = message.get_payload(decode=True)
            if content:
                charset = message.get_content_charset()
                try:
                    return content.decode(charset or "utf-8")
                except (UnicodeDecodeError, TypeError):
                    return content.decode("latin1", errors="ignore")
        return ""


# 메일 회신 함수 정의
def create_reply(email_message, reply_message, from_addr):
    reply_to = email_message.get("Reply-To", email_message["From"])
    reply = EmailMessage()
    reply["To"] = reply_to
    reply["From"] = from_addr
    reply["Subject"] = "Re: " + email_message["Subject"]
    reply["In-Reply-To"] = email_message["Message-ID"]
    reply["References"] = (
        email_message.get("References", "") + " " + email_message["Message-ID"]
    ).strip()
    reply.set_content(reply_message)
    return reply


# 메일 전송 함수 정의
def send_email(message, email_id, email_password):
    smtp_server = "smtp.naver.com"
    port = 587
    username = email_id
    password = email_password
    with smtplib.SMTP(smtp_server, port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(message)


# 답장 textarea 공간 조절 함수 정의
def enable_auto_resize_textareas():
    components.html(
        """
        <script>
        const resizeTextareas = () => {
            const textareas = window.parent.document.querySelectorAll("textarea");
            textareas.forEach((textarea) => {
                if (textarea.dataset.autoResizeBound === "true") {
                    textarea.style.height = "auto";
                    textarea.style.height = `${textarea.scrollHeight}px`;
                    return;
                }

                const resize = () => {
                    textarea.style.height = "auto";
                    textarea.style.height = `${textarea.scrollHeight}px`;
                };

                textarea.dataset.autoResizeBound = "true";
                textarea.style.overflowY = "hidden";
                textarea.style.resize = "none";
                textarea.addEventListener("input", resize);
                resize();
            });
        };

        const observer = new MutationObserver(resizeTextareas);
        observer.observe(window.parent.document.body, {
            childList: true,
            subtree: true,
        });

        resizeTextareas();
        </script>
        """,
        height=0,
    )


def main():
    st.set_page_config(layout="wide")
    enable_auto_resize_textareas()
    st.title("메일 자동 응답 프로그램")
    st.caption("최근 수신한 메일을 확인하고 답장 초안을 작성합니다.")

    # 주요 세션 상태 변수 선언
    if "openai_api_key" not in st.session_state:
        st.session_state.openai_api_key = None
    if "email_id" not in st.session_state:
        st.session_state.email_id = None
    if "email_password" not in st.session_state:
        st.session_state.email_password = None
    if "emails" not in st.session_state:
        st.session_state.emails = None
    if "client" not in st.session_state:
        st.session_state.client = None
    if "answer_generated" not in st.session_state:  # 답장 초안
        st.session_state.answer_generated = None
    if "generated_answer" not in st.session_state:
        st.session_state.generated_answer = ""
    if "final_reply" not in st.session_state:  # 최종 메일
        st.session_state.final_reply = None

    # 사이드바 생성
    with st.sidebar:
        st.session_state.openai_api_key = st.text_input(
            "OpenAI API Key", type="password"
        )
        st.write("[OpenAI API Key 받기](https://platform.openai.com/account/api-keys)")
        st.session_state.email_id = st.text_input("네이버 아이디", key="id")
        st.session_state.email_password = st.text_input(
            "네이버 비밀번호", key="password"
        )

    # 열 레이아웃 생성
    col1, col2 = st.columns([1.5, 1])
    with col1:
        if st.button("메일 불러오기"):
            if not (
                st.session_state.openai_api_key
                and st.session_state.email_id
                and st.session_state.email_password
            ):
                st.error("API Key, 네이버 아이디와 비밀번호를 입력하세요.")
                st.stop()
            with st.spinner("메일 불러오는 중..."):
                emails_df = fetch_emails(
                    st.session_state.email_id, st.session_state.email_password
                )

                # 메일 데이터프레임 세션 상태 변수 선언
                if emails_df is not None:
                    st.session_state.emails = emails_df

        if st.session_state.emails is not None:
            # 메일 데이터프레임 출력
            selected_email = st.dataframe(
                st.session_state.emails[["날짜", "발신인", "제목"]],
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                use_container_width=True,
            )
            # 특정 행 선택 시 해당 내용 출력
            if selected_email["selection"]["rows"]:
                selected_index = selected_email["selection"]["rows"][0]
                selected_row = st.session_state.emails.iloc[selected_index]
                email_subject = selected_row["제목"]
                sender = selected_row["발신인"]
                email_content = selected_row["본문"]
                message_object = selected_row["메일 객체"]
                st.write("제목: " + email_subject)
                st.write("발신인: " + sender)
                st.write(email_content)
            else:
                st.write("메일을 선택하세요.")
    with col2:
        # 답장 작성을 위한 프롬프트 입력 위젯 생성
        default_user_prompt = """- 반드시 한글로 작성해.
        - 구체적인 상황을 설명해달라는 내용으로 작성해.
        - 친절하게 작성해.
        """
        user_input = st.text_area(
            "메일 답장 방식을 작성해주세요.",
            value=default_user_prompt,
            height=100,
            key="reply_style_prompt",
        )
        generate_answers = st.button("답장 초안 작성")
        if generate_answers:
            st.session_state.client = OpenAI(api_key=st.session_state.openai_api_key)
            with st.spinner("답장 초안 작성 중..."):
                # (16) 최종 프롬프트로 답장 초안 생성
                prompt = f"""
                메일 발신인: {sender}
                메일 내용: {email_content}
                너는 위 메일에 대해 답장을 작성하는 사람이야.
                {user_input}
                """
                response = st.session_state.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": prompt}],
                )
                result_text = response.choices[0].message.content

            # 답장 초안의 세션상태 반영
            st.session_state.generated_answer = result_text
            st.session_state.answer_generated = True
        if st.session_state.answer_generated:
            # 답장 초안 출력
            st.session_state.final_reply = st.text_area(
                "AI 답장 초안",
                value=st.session_state.generated_answer,
                height=300,
                key="final_reply_input",
            )

            # 메일 회신 버튼
            if st.button("메일 회신하기"):
                with st.spinner("메일 회신 중..."):
                    from_addr = f"{st.session_state.email_id}@naver.com"
                    reply_message = st.session_state.final_reply
                    reply_email = create_reply(message_object, reply_message, from_addr)
                    send_email(
                        reply_email,
                        st.session_state.email_id,
                        st.session_state.email_password,
                    )
                st.success("메일을 성공적으로 발송했습니다.")


if __name__ == "__main__":
    main()
