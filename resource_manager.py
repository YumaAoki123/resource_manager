from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta, timezone, date, time
import pytz
from dotenv import load_dotenv
import os
import json



# タスクを保存するためのリスト
tasks = []

load_dotenv()

email = os.getenv('EMAIL')
DATA_FILE = 'tasks.json'

# タスクデータをファイルから読み込む関数
def load_tasks():
    global tasks
    try:
        with open(DATA_FILE, "r") as f:
            tasks = json.load(f)
    except FileNotFoundError:
        tasks = []

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



def save_selected_period(task_name, task_duration, start_date, end_date):
    # JST タイムゾーンを設定
    jst = pytz.timezone('Asia/Tokyo')

    # start_date と end_date が datetime オブジェクトであることを確認し、タイムゾーンを設定
    if isinstance(start_date, datetime):
        start_date_jst = start_date.astimezone(jst)
    elif isinstance(start_date, date):
        # date オブジェクトから datetime オブジェクトを作成（時間は 00:00 とする）
        start_date_jst = datetime.combine(start_date, time(0, 0))
        start_date_jst = jst.localize(start_date_jst)
    else:
        raise ValueError("start_date は datetime または date オブジェクトでなければなりません")

    if isinstance(end_date, datetime):
        end_date_jst = end_date.astimezone(jst)
    elif isinstance(end_date, date):
        # date オブジェクトから datetime オブジェクトを作成（時間は 00:00 とする）
        end_date_jst = datetime.combine(end_date, time(0, 0))
        end_date_jst = jst.localize(end_date_jst)
    else:
        raise ValueError("end_date は datetime または date オブジェクトでなければなりません")

    # 日付を ISO 8601 形式の文字列に変換
    start_date_iso = start_date_jst.isoformat()
    end_date_iso = end_date_jst.isoformat()

    # データを JSON 形式にして保存
    period_data = {
        "task_name": task_name,
        "task_duration": task_duration,
        "start_date": start_date_iso,
        "end_date": end_date_iso,
       
    }

    # JSON ファイルに保存
    with open('selected_period.json', 'w') as file:
        json.dump(period_data, file, ensure_ascii=False, indent=4)

def load_selected_period():
    with open("selected_period.json", "r") as f:
        period_data = json.load(f)
        
        # ISO 8601形式の文字列をdatetimeオブジェクトに変換
        start_date = datetime.fromisoformat(period_data["start_date"])
        end_date = datetime.fromisoformat(period_data["end_date"])
        
        # 既にタイムゾーン情報が含まれているので、JSTに変換する必要はない
        # そのまま使用する
        # JSTに変換する場合（必要ならコメントアウトを解除してください）
        # japan_tz = pytz.timezone('Asia/Tokyo')
        # start_time = start_date.astimezone(japan_tz)
        # end_time = end_date.astimezone(japan_tz)
        
        # JSTに変換せず、そのまま使用する場合
        start_time = start_date
        end_time = end_date
        
        # その他のデータの取得
        task_name = period_data.get("task_name", 0)
        sleep_hours = period_data.get("sleep_hours", 0)
        meal_hours = period_data.get("meal_hours", 0)
        commute_hours = period_data.get("commute_hours", 0)
        
        return task_name, start_time, end_time, sleep_hours, meal_hours, commute_hours
    
    
def get_minutes_set(start, end):
    """開始時間と終了時間の間の時間を分単位でセットとして返す"""
    current = start
    minutes_set = set()
    while current < end:
        minutes_set.add(current)
        current += timedelta(minutes=1)
    return minutes_set


def process_period_data():
    task_name, start_time, end_time, sleep_hours, meal_hours, commute_hours = load_selected_period()
    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    print(f"sleep_hours Time: {sleep_hours}")
    print(f"meal_hours Time: {meal_hours}")

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
        while current_time < end_time:
            if not is_excluded_weekday(current_time):
                total_hours += 24  # 1日を24時間としてカウント
              
            current_time += timedelta(days=1)
        
        sum_others = sleep_hours + meal_hours + commute_hours
        free_hours = total_hours - total_duration_hours - sleep_hours - meal_hours - commute_hours
        

        # イベントのタイトルと時間を出力
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            print(f'タイトル: {event["summary"]} 開始日時: {start}')
            print(f'タイトル: {event["summary"]} 終了日時: {end}')
            print('---')
            
        return free_hours, total_duration_hours, sum_others, total_hours
    
def get_free_times(start_time, end_time, calendar_id=email):
    
  # 空き時間のリスト
    free_times = []
  # JST タイムゾーンを設定
    jst = pytz.timezone('Asia/Tokyo')
    
    # 日本時間からUTCに変換(googlecalendarapiがutcじゃないと読み取らないらしい)
    start_time_utc = start_time.astimezone(pytz.UTC)
    end_time_utc = end_time.astimezone(pytz.UTC)
    print(f"Request Body: {start_time_utc}")  # デバッグ用
    # リクエストのボディを作成
    request_body = {
        "timeMin": start_time_utc.isoformat(),
        "timeMax": end_time_utc.isoformat(),
        "timeZone": "Asia/Tokyo",  # レスポンスのタイムゾーン
        "items": [{"id": calendar_id}]
    }
    
    print(f"Request Body: {request_body}")  # デバッグ用
    
    # freebusyリクエストを送信
    freebusy_result = service.freebusy().query(body=request_body).execute()

    busy_times = freebusy_result['calendars'][calendar_id]['busy']

      # 予定のある時間帯を計算
    busy_periods = []
    for busy_period in busy_times:
        start = busy_period['start']
        end = busy_period['end']
        
        # 日本時間に変換
        start_time_jst = datetime.fromisoformat(start).astimezone(jst)
        end_time_jst = datetime.fromisoformat(end).astimezone(jst)
        
        busy_periods.append((start_time_jst, end_time_jst))

    # 予定のない時間帯を計算
    busy_periods.sort()  # 予定のある時間帯をソート
    current_start = start_time

    for busy_start, busy_end in busy_periods:
        # 現在の空き時間の終了が予定の開始より前であれば、その間が空き時間
        if busy_start > current_start:
            free_times.append((current_start, busy_start))
        # 現在の空き時間の開始を予定の終了時間に更新
        current_start = max(current_start, busy_end)

    # 最後の空き時間を追加
    if current_start < end_time:
        free_times.append((current_start, end_time))

    # 空き時間を出力
    for free_start, free_end in free_times:
        print(f"空いている時間帯: start_time: {free_start} から end_time: {free_end}")

    return free_times
