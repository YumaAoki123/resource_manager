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


#追加する予定の情報を取得

#追加する予定の分割

#条件設定

#既存のイベントとの比較　すでに予定があるところにはスキップ





calendar_list_entry = {
    # 予定のタイトル
    'summary': 'ミーティング③',
    # 予定の開始時刻
    'start': {
        'dateTime': datetime(2024, 8, 10, 10, 30).isoformat(),
        'timeZone': 'Asia/Tokyo'
    },
    # 予定の終了時刻
    'end': {
        'dateTime': datetime(2024, 8, 10, 12, 0).isoformat(),
        'timeZone': 'Asia/Tokyo'
    },
}

# 予定を追加
created_event = service.events().insert(calendarId=email, body=calendar_list_entry).execute()

print(created_event['summary'])