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
import json
from google.oauth2.credentials import Credentials


os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # HTTPSを強制しないようにする（ローカル開発用）
client_id = os.environ['GOOGLE_CLIENT_ID']
client_secret = os.environ['GOOGLE_CLIENT_SECRET']
# 認可のためのスコープ
scope = ["https://www.googleapis.com/auth/calendar"]

# トークンをデータベースに保存する関数
def save_token_to_db(user_id, credentials):
        # バイナリ形式でシリアライズ
    token_data = pickle.dumps(credentials)  # credentialsをバイナリデータに変換
    print(f'user_id_passed:{user_id}')
    # ユーザーのトークンが既に存在する場合は更新、なければ新規作成
    user_token = db.query(Token).filter_by(user_id=user_id).first()
    
    if user_token:
        user_token.token_data = token_data
    else:
        user_token = Token(user_id=user_id, token_data=token_data)
        db.add(user_token)

    db.commit()

# トークンをデータベースから取得する関数
def get_credentials(user_id):
        # 実行環境に応じたファイルパスの取得
    if getattr(sys, 'frozen', False):
        # PyInstallerでパッケージ化された場合
        base_path = sys._MEIPASS
    else:
        # 開発中の場合
        base_path = os.path.dirname(__file__)

        # credentials.jsonのパスを組み立てる
    credentials_path = os.path.join(base_path, 'credentials.json')

    credentials = None
    print(f'user_id:{user_id}')
    # データベースからユーザーのトークンを取得
    user_token = db.query(Token).filter_by(user_id=user_id).first()

    if user_token:
        # BLOBデータをデシリアライズ
        credentials = pickle.loads(user_token.token_data)
        
        # デバッグ: credentialsの内容を確認
        print(f"Debug: Credentials for user_id {user_id}: {credentials}")

    # トークンが存在しないか、期限切れの場合は新規取得
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            # トークンを更新
            credentials.refresh(Request())
        else:
            # 新しいトークンを取得
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scope)
            credentials = flow.run_local_server(port=0)

        # 新しいトークンをデータベースに保存
        save_token_to_db(user_id, credentials)

    return credentials
    

def calculate_free_times(start_date, end_date, user_id, calendar_id="primary"):
    print(f'user_id:{user_id}')
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
    credentials = get_credentials(user_id)
    # Google Calendar APIのサービスオブジェクトを作成
    service = build('calendar', 'v3', credentials=credentials)
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
