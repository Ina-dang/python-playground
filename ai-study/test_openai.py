import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

# 사용자&AI 대화 내역 저장
message_history = []

while True:

    # 사용자 입력
    user_input = input("사용자: ")
    message_history.append({"role": "user", "content": user_input})
    chat_completion = client.chat.completions.create(
        model="gpt-4o",
        messages=message_history,  # 이전 대화 내역 모두 저장
    )

    # AI 응답
    assistant_response = chat_completion.choices[0].message.content
    message_history.append({"role": "assistant", "content": assistant_response})

    print(f"챗봇: {assistant_response}")
