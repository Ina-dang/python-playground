import streamlit as st
from openai import OpenAI
import re


# 여행 일정 함수 정의
def generate_travel_plan(city, trip_duration, client):
    prompt = f"""
    ## 요청 사항
      너는 여행 계획 전문가야.
      - 입력받은 도시와 여행 기간에 맞춰 여행 일정을 작성해.
      - 여행 기간은 {trip_duration}이야.
      - 각 날짜는 반드시 ## 1일차, ## 2일차 같은 형식의 heading2로 시작해.
      - 각 날짜 아래에는 ### 오전, ### 오후, ### 저녁 소제목을 모두 포함해.
      - 오전, 오후, 저녁 일정마다 2줄씩 bullet point로 작성해.
      - 일정 외의 설명은 쓰지 마.
      - 일정은 구체적이고 친절하게 작성해.

      ## 응답 예시(도시: 이스탄불, 기간: 1박 2일)
      ## 1일차
      ### 오전
      - 아침 일찍 일어나 블루 모스크(술탄 아흐메트 모스크)를 방문하세요. 오전의 햇살 속에서 더욱 아름답습니다.
      - 블루 모스크 내부의 멋진 타일과 아치형 구조를 감상하며 걸어보세요. 무료 입장이 가능합니다.
      ### 오후
      - 그랜드 바자르를 방문해 현지의 다양한 상품을 구경하고 쇼핑을 즐기세요. 활기찬 분위기를 느낄 수 있습니다.
      - 바자르에서 가까운 스파이스 바자르로 이동해 향신료와 터키 과자를 구입하세요. 향이 그윽한 시장입니다.
      ### 저녁
      - 저녁에는 보스포루스 해협 유람선을 타고 도시의 아름다운 야경을 감상하세요. 해가 질 때의 풍경이 특히 장관입니다.
      - 유람선 투어 후 이슬람 문화의 향기를 느낄 수 있는 근처의 레스토랑에서 저녁 식사를 즐기세요.

      ## 2일차
      ### 오전
      - 현지 카페에서 아침 식사를 즐긴 뒤 갈라타 타워 주변 골목을 천천히 산책하세요.
      - 기념품 가게를 둘러보며 여행 마지막 날의 여유를 느껴보세요.
      ### 오후
      - 공항이나 기차역으로 이동하기 전 근처 명소 한 곳을 가볍게 둘러보세요.
      - 남은 시간에는 현지 음식점에서 마지막 식사를 하며 여행을 마무리하세요.
      ### 저녁
      - 귀가 일정이 있다면 교통편 시간을 확인하고 여유 있게 이동하세요.
      - 숙소에 머무는 경우에는 주변 야경 명소에서 차분하게 하루를 정리하세요.
    """

    content = prompt + f"\n도시: {city}\n여행 기간: {trip_duration}"
    response = client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": content}]
    )
    return response.choices[0].message.content


# 여행 일정 분할 함수 정의
def parse_plan(input_text):
    sections = re.split(r"(?=##\s+\d+일차)", input_text)
    plan_items = []

    for section in sections:
        section = section.strip()
        if not section:
            continue
        lines = section.splitlines()
        day_title = lines[0].replace("##", "").strip()
        day_content = "\n".join(lines[1:]).strip()
        plan_items.append({"title": day_title, "content": day_content})

    return plan_items


# 이미지 생성 함수 정의
def generate_image_url(prompt: str, client):
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
    )
    return response.data[0].url


def main():
    st.set_page_config(layout="wide")
    st.title("여행 일정 가이드 프로그램")

    with st.sidebar:
        st.subheader("OpenAI API key 설정")
        openai_api_key = st.text_input("OpenAI API Key", type="password")
        st.write("[OpenAI API Key 받기](https://platform.openai.com/account/api-keys)")

    if openai_api_key:
        client = OpenAI(api_key=openai_api_key)

    # 도시 입력
    user_input = st.text_input("여행 가고 싶은 도시를 입력하세요.", value="이스탄불")
    nights = st.number_input("숙박 일수", min_value=1, max_value=30, value=3, step=1)
    days = st.number_input("여행 일수", min_value=1, max_value=31, value=4, step=1)
    trip_duration = f"{nights}박 {days}일"

    if st.button("여행 계획 작성"):
        if not openai_api_key:
            st.error("유효한 API Key를 입력하세요.")
            st.stop()
        if not user_input.strip():
            st.warning("여행 가고 싶은 도시를 입력하세요.")
            st.stop()
        if days < nights:
            st.warning("여행 일수는 숙박 일수보다 같거나 커야 합니다.")
            st.stop()
        with st.spinner("여행 계획 작성 중..."):
            travel_plan = generate_travel_plan(user_input, trip_duration, client)
            plan_items = parse_plan(travel_plan)

            # 일차 별 여행 일정 출력
            for item in plan_items:
                col1, col2 = st.columns([3, 2])
                with col1:
                    st.write("## " + item["title"])
                    st.write(item["content"])
                with col2:
                    # 일차 별 이미지 생성
                    img_url = generate_image_url(
                        f"{user_input} 여행 {item['title']} 일정 이미지", client
                    )
                    st.image(img_url)


if __name__ == "__main__":
    main()
