# calendar_service.py
from googleapiclient.discovery import build
import pytz
from datetime import datetime
import os
import os.path
import sys
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from model.models import User, Token, db
from flask import session
# 認証に必要なスコープ
SCOPES = [
    'https://www.googleapis.com/auth/calendar'
]


def get_credentials():
    creds = None
    # Flaskセッションからユーザー名を取得
    username = session.get('username')
    if not username:
        raise ValueError("No username found in session.")
    
    # データベースからユーザーを取得
    user = db.query(User).filter_by(username=username).first()
    if not user:
        raise ValueError(f"User with username {username} does not exist.")
    print(f'user:{user}')
    # データベースからユーザーのトークン情報を取得
    token = db.query(Token).filter_by(user_id=user.id).first()
    print(f'token:{token}')
   
    if token and token.google_creds:
        try:
            creds = pickle.loads(token.google_creds)  # `creds` オブジェクト全体を読み込む
            print("Deserialized Credentials:", creds)
            print("Type of Credentials:", type(creds))  # データ型の確
            if creds and creds.valid:

                return creds
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                # 更新したトークンを保存
                token.google_creds = pickle.dumps(creds)  # `creds` オブジェクト全体を保存
                db.commit()
                return creds
        except Exception as e:
            print(f'Error loading credentials: {e}')
    
    # トークンが存在しないか無効な場合、新しい認証を行う
    credentials_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
    creds = flow.run_local_server(port=0)
    
    # 新しいトークンをデータベースに保存
    new_token = Token(
        user_id=user.id,
        google_creds=pickle.dumps(creds),  # `creds` オブジェクト全体を保存
    )
    db.add(new_token)
    db.commit()

    return creds


# Google Calendar API を使うための準備
def get_calendar_service():
    creds = get_credentials()
    calendar_service = build('calendar', 'v3', credentials=creds)
    return calendar_service
    

def calculate_free_times(start_date, end_date, calendar_id="primary"):
    free_times = []
    print(f'start_date:{start_date}')
    # JST タイムゾーンを設定
    jst = pytz.timezone('Asia/Tokyo')
    
    # 文字列を datetime オブジェクトに変換
    start_date_datetime = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S%z")
    end_date_datetime = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S%z")

    # UTC に変換
    start_time_utc = start_date_datetime.astimezone(pytz.UTC)
    end_time_utc = end_date_datetime.astimezone(pytz.UTC)

    # Freebusy リクエストのボディを作成
    request_body = {
        "timeMin": start_time_utc.isoformat(),
        "timeMax": end_time_utc.isoformat(),
        "timeZone": "Asia/Tokyo",  # レスポンスのタイムゾーン
        "items": [{"id": calendar_id}]
    }
    service = get_calendar_service()
    # Freebusy リクエストを送信
    freebusy_result = service.freebusy().query(body=request_body).execute()

    busy_times = freebusy_result['calendars'][calendar_id]['busy']

    # 予定のある時間帯を計算
    busy_periods = []
    for busy_period in busy_times:
        start = busy_period['start']
        end = busy_period['end']

        # 日本時間に変換
        start_time_jst = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(jst)
        end_time_jst = datetime.fromisoformat(end.replace("Z", "+00:00")).astimezone(jst)

        busy_periods.append((start_time_jst, end_time_jst))

    # 予定のない時間帯を計算
    busy_periods.sort()  # 予定のある時間帯をソート
    current_start = start_date_datetime.astimezone(jst)

    for busy_start, busy_end in busy_periods:
        # 予定のある時間帯の間に空き時間があれば追加
        if busy_start > current_start:
            free_times.append((current_start, busy_start))
        
        # 空き時間の開始を更新
        current_start = max(current_start, busy_end)

    # 最後の空き時間を追加
    if current_start < end_date_datetime:
        free_times.append((current_start, end_date_datetime))

    return free_times
