import arrow
import openai
import os
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta
from add_schedule import add_schedule
from delete_schedule import delete_schedule
from select_schedule import select_schedule
from weather_info import get_weather_info
from speaker import speak

# secret API 키를 가져오기 위해 .env file 로드
load_dotenv()

# API key 가져오기
openai.api_key = os.getenv("GPT_API_KEY")

# AI에게 역할을 부여
messages = [
    {"role": "system", "content": (
        "You are an advanced personal assistant AI. "
        "Your tasks include managing user schedules and providing weather information. "
        "For managing schedules, you will handle requests such as adding, deleting, and showing schedules. "
        "For weather information, you will provide current weather and forecasts."
    )}
]

#GPT 모델에 prompt를 전달해 response 생성
def generate_gpt_response(prompt):
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  #GPT 모델
        messages=[{"role": "user", "content": prompt}], # 사용자 입력을 포함한 메시지
        temperature=0.7,    # 응답의 창의성 정도
        max_tokens=100  # 응답의 최대 길이
    )
    response = completion.choices[0].message["content"].strip() #응답에서 내용 추출, 양쪽 공백 제거
    return response

#GPT 응답에서 user name, date, time, task 추출
def parse_gpt_schedule_instruction(user_input):
    prompt = (
        f"다음 문장에서 '사용자 이름', '날짜', '시간', '일정 내용'을 각각 추출하세요:\n"
        f"'{user_input}'\n"
        f"출력 형식: '사용자 이름: 유리, 날짜: 2024-08-05, 시간: 10:30, 일정 내용: 인형 사기' 이런 형식으로 출력하세요."
    )
    response = generate_gpt_response(prompt)

    # 정규 표현식을 사용하여 필요한 정보를 추출
    match = re.search(r"사용자 이름: (.+?), 날짜: (.+?), 시간: (.+?), 일정 내용: (.+)", response)
    if match:
        user_name = match.group(1).strip()
        date = match.group(2).strip()
        time = match.group(3).strip()
        task = match.group(4).strip()

        # 날짜와 시간을 형식에 맞추기
        if "내일" in date:
            date = (arrow.now().shift(days=1)).format('YYYY-MM-DD')
        elif "오늘" in date:
            date = arrow.now().format('YYYY-MM-DD')
        elif "다음주" in date:
            day_of_week = re.search(r"(월요일|화요일|수요일|목요일|금요일|토요일|일요일)", date)
            if day_of_week:
                day_map = {'월요일': 0, '화요일': 1, '수요일': 2, '목요일': 3, '금요일': 4, '토요일': 5, '일요일': 6}
                target_day = day_map[day_of_week.group(1)]
                date = (arrow.now().shift(weeks=1).shift(days=(target_day - arrow.now().weekday()))).format('YYYY-MM-DD')

        if "시" in time:
            time = time.replace("시", ":").replace(" ", "")
            if len(time) == 2:
                time += ":00"
            elif len(time.split(":")[1]) == 1:
                time += "0"
            time += ":00"

        # 일정 내용에서 불필요한 단어 제거
        task = re.sub(r"(추가해줘|해줘|하세요|해)", "", task).strip()

        return user_name, date, time, task
    else:
        return None, None, None, None

# 날씨 예보를 제공할 날짜
def determine_forecast_day(user_input):
    if "오늘" in user_input or "today" in user_input:
        return 0
    elif "내일" in user_input or "tomorrow" in user_input:
        return 1
    elif "모레" in user_input:
        return 2
    else:
        return None

#사용자 입력에서 날짜와 시간을 추출
def extract_date_and_time(user_input):
    #날짜, 요일 추출
    date_match = re.search(r'(다음주|이번주|내일|오늘|모레)\s*(월요일|화요일|수요일|목요일|금요일|토요일|일요일)?', user_input)
    #시간 추출
    time_match = re.search(r'(\d{1,2})시(?:\s(\d{1,2})분)?', user_input)
    #날짜 추출 : 이번주와 다음주만 저장 가능 (다른 주는 날짜로 말해야 함)
    if date_match:
        if date_match.group(1) == '다음주':
            base_date = arrow.now().shift(weeks=1)
        else:
            base_date = arrow.now()
        #요일 추출
        if date_match.group(2):
            weekday_str = date_match.group(2)
            weekday_dict = {'월요일': 0, '화요일': 1, '수요일': 2, '목요일': 3, '금요일': 4, '토요일': 5, '일요일': 6}
            target_weekday = weekday_dict[weekday_str]
            #요일을 날짜로 바꿈
            days_diff = (target_weekday - base_date.weekday()) % 7
            target_date = base_date.shift(days=days_diff).format('YYYY-MM-DD')
        elif "내일" in date_match.group(1):
            target_date = arrow.now().shift(days=1).format('YYYY-MM-DD')    #내일 이면 현재 날짜에 +1
        elif "오늘" in date_match.group(1):
            target_date = arrow.now().format('YYYY-MM-DD')
        elif "모레" in date_match.group(1):
            target_date = arrow.now().shift(days=2).format('YYYY-MM-DD')
    else:
        target_date = arrow.now().format('YYYY-MM-DD')  #날짜 없으면 오늘 날짜로 지정
    #시간 추출
    if time_match:
        hour = time_match.group(1).zfill(2) #시
        minute = time_match.group(2).zfill(2) if time_match.group(2) else '00'  #분
        target_time = f"{hour}:{minute}:00" #초
    else:
        target_time = "00:00:00"    #시간 없으면 00시00분00초

    return target_date, target_time
#사용자의 입력이 날씨 요청인지 확인 : 입력에 "날씨", "weather" 있으면 true
def is_weather_request(user_input):
    return "날씨" in user_input or "weather" in user_input
#사용자의 입력이 일정 관리 요청인지 확인 : 입력에 "일정", "추가", "삭제", "알려줘", "말해줘" 있으면 true
def is_schedule_request(user_input):
    return "일정" in user_input or "추가" in user_input or "삭제" in user_input or "알려줘" in user_input or "말해줘" in user_input

while True:
    #사용자에게 입력을 받음
    user_content = speak()
    if user_content is None:
        print("Please try speaking again.")
        continue

    #날씨 요청을 처리
    if "날씨" in user_content:    #입력에 "날씨"가 있으면
        forecast_day = determine_forecast_day(user_content) #날짜를 return
        if forecast_day is not None:    #오늘, 내일, 모레 이면
            weather_info = get_weather_info(forecast_day)   #weather_info.py 함수에서 날짜 가져옴
            print(f"assistant: {weather_info}") #날씨 출력
        continue
    #일정 관리 요청을 처리
    elif is_schedule_request(user_content): #입력에 일정이 있으면
        user_name, date, time, task = parse_gpt_schedule_instruction(user_content)
        #print(f"GPT 응답: 사용자 이름: {user_name}, 날짜: {date}, 시간: {time}, 일정 내용: {task}")  # 디버그 로그
        if "추가" in user_content:
            response = add_schedule(user_name, date, time, task)
            print(f"assistant: {response}")
        elif "삭제" in user_content:
            response = delete_schedule(user_name, date, time)
            print(f"assistant: {response}")
        elif "알려줘" in user_content or "말해줘" in user_content:
            schedules = select_schedule(user_name, date)
            if schedules:   #user_name, date 받아서 그 날, 그 사용자에게 일정이 있다면
                response = f"{user_name}의 {date} 일정:\n" #출력
                for schedule in schedules:
                    response += f"{schedule[0]}: {schedule[1]}\n"   #사용자 이름, 날짜 일치하는 행 모두
            else:   #그 날, 사용자 일정이 없다면
                response = f"{user_name}의 {date} 일정이 없습니다."
            print(f"assistant: {response}")
            continue
    # #GPT에게 사용자 입력을 전달해 응답을 받음
    # messages.append({"role": "user", "content": user_content})
    #
    # completion = openai.ChatCompletion.create(
    #     model="gpt-3.5-turbo",
    #     messages=messages,
    #     temperature=0.7,
    #     max_tokens=1024
    # )
    #
    # ai_message = completion.choices[0].message["content"].strip()
    # messages.append({"role": "assistant", "content": ai_message}) # 생성된 응답을 대화 내역에 추가하고 출력
    # print(f"assistant: {ai_message}")

    # GPT 모델에 사용자 입력을 전달하여 응답을 생성
    prompt = user_content  # 사용자 입력을 프롬프트로 사용
    ai_message = generate_gpt_response(prompt)  # 응답 생성

    # 생성된 응답을 대화 내역에 추가하고 출력
    messages.append({"role": "assistant", "content": ai_message})
    print(f"assistant: {ai_message}")

#사용자가 exit, bye라고 입력하면 종료
    if user_content.lower() in ['exit', 'bye']:
        print("! bye !")
        break