from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta, timezone
import pytz
from dotenv import load_dotenv
import os
import json

load_dotenv()

email = os.getenv('EMAIL')

# サービスアカウントキーファイルのパスを指定する
SERVICE_ACCOUNT_FILE = '/resource_manager/creditials.json'

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ファイルパスを引数として渡す
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Google Calendar API を使うための準備
service = build('calendar', 'v3', credentials=credentials)

# 特定の曜日を除外するための関数
def is_excluded_weekday(date):
    return date.weekday() in [5, 6]  # 土曜日(5)と日曜日(6)を除外



def save_selected_period(start_date, end_date):
    period_data = {
        "start_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d")
    }
    with open("selected_period.json", "w") as f:
        json.dump(period_data, f)

def load_selected_period():
    with open("selected_period.json", "r") as f:
        period_data = json.load(f)
        japan_tz = pytz.timezone('Asia/Tokyo')
        start_date = datetime.strptime(period_data["start_date"], "%Y-%m-%d")
        end_date = datetime.strptime(period_data["end_date"], "%Y-%m-%d")
        start_time = japan_tz.localize(start_date)
        end_time = japan_tz.localize(end_date)
        return start_time, end_time
    
    
def get_minutes_set(start, end):
    """開始時間と終了時間の間の時間を分単位でセットとして返す"""
    current = start
    minutes_set = set()
    while current < end:
        minutes_set.add(current)
        current += timedelta(minutes=1)
    return minutes_set


def process_period_data():
    start_time, end_time  = load_selected_period()
    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")

    delta = end_time - start_time
    days_count = delta.days

    # 日付をISO 8601形式に変換してクエリを作成
    start_time_str = start_time.isoformat()
    end_time_str = end_time.isoformat()

    # カレンダーIDを指定してイベントを取得するリクエストを作成
    events_result = service.events().list(calendarId=email, timeMin=start_time_str, timeMax=end_time_str, singleEvents=True, orderBy='startTime').execute()

    # 取得したイベントを処理する
    events = events_result.get('items', [])
    if not events:
        print('指定した期間にイベントはありませんでした。')
    else:
        all_minutes = set()  # すべてのイベントの時間範囲を格納するセット

        # イベントの開始時間と終了時間をdatetimeオブジェクトに変換
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            event_start_time = datetime.fromisoformat(start.replace('Z', ''))
            event_end_time = datetime.fromisoformat(end.replace('Z', ''))

              # 特定の曜日を除外
            if is_excluded_weekday(event_start_time) or is_excluded_weekday(event_end_time):
                continue

            if (event_start_time.time() == datetime.min.time() and event_end_time.time() == datetime.min.time()):
                continue

            # イベントの時間範囲をセットとして取得し、全体のセットに統合
            event_minutes_set = get_minutes_set(event_start_time, event_end_time)
            all_minutes = all_minutes.union(event_minutes_set)

        # 合計時間を計算
        total_duration_minutes = len(all_minutes)
        total_duration_hours = total_duration_minutes / 60  # 時間単位に変換
        current_time = start_time
        total_hours = 0
        sleep_hours = 0
        meal_hours = 0
        commute_hours = 0
        while current_time < end_time:
            if not is_excluded_weekday(current_time):
                total_hours += 24  # 1日を24時間としてカウント
                sleep_hours += 6 
                meal_hours += 1.66
                commute_hours += 1.33
            current_time += timedelta(days=1)
        
        sum_others = sleep_hours + meal_hours + commute_hours
        free_hours = total_hours - total_duration_hours - sleep_hours - meal_hours - commute_hours
        

        # イベントのタイトルと時間を出力
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
           # print(f'タイトル: {event["summary"]} 開始日時: {start}')
            #print(f'タイトル: {event["summary"]} 終了日時: {end}')
            #print('---')
        return free_hours, total_duration_hours, sum_others, total_hours
    
     
      


    


       
   