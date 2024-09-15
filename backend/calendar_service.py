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

# 認証に必要なスコープ
SCOPES = [
    'https://www.googleapis.com/auth/calendar'
]

TOKEN_PICKLE = 'token.pickle'

# ユーザーごとにトークンを保存するための関数
def save_token_to_db(user, creds):
    # 既存のトークンがあるか確認
    token_entry = db.query(Token).filter_by(user_id=user.id).first()
    
    # トークンがすでに存在する場合は更新、存在しない場合は新規作成
    if token_entry:
        token_entry.access_token = creds.token
        token_entry.refresh_token = creds.refresh_token
        token_entry.token_expiry = creds.expiry
    else:
        new_token = Token(
            user_id=user.id,
            access_token=creds.token,
            refresh_token=creds.refresh_token,
            token_expiry=creds.expiry
        )
        db.add(new_token)
    
    db.commit()
    db.close()

def get_credentials():
    creds = None
    # 実行環境に応じたファイルパスの取得
    if getattr(sys, 'frozen', False):
        # PyInstallerでパッケージ化された場合
        base_path = sys._MEIPASS
    else:
        # 開発中の場合
        base_path = os.path.dirname(__file__)

    # credentials.jsonのパスを組み立てる
    credentials_path = os.path.join(base_path, 'credentials.json')

    # 既にトークンが存在する場合、それを読み込む
    if os.path.exists(TOKEN_PICKLE):
        with open(TOKEN_PICKLE, 'rb') as token:
            creds = pickle.load(token)
    # トークンがないか、無効または期限切れの場合、新しく認証を行う
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        # トークンを保存
        with open(TOKEN_PICKLE, 'wb') as token:
            pickle.dump(creds, token)
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
