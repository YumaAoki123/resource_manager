from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta, timezone
import pytz
from dotenv import load_dotenv
import os
import json
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from tkcalendar import DateEntry
import customtkinter as ctk
import json
from resource_manager import save_selected_period, process_period_data  # バックエンドの関数をインポート
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt

# タスクを保存するためのリスト
tasks = []

SELECTED_PERIOD_FILE = 'selected_period.json'
DATA_FILE = 'tasks.json'
load_dotenv()

email = os.getenv('EMAIL')

# サービスアカウントキーファイルのパスを指定する
SERVICE_ACCOUNT_FILE = '/resource_manager/creditials.json'

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# ファイルパスを引数として渡す
credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Google Calendar API を使うための準備
service = build('calendar', 'v3', credentials=credentials)

DATA_FILE = 'tasks.json'
#追加する予定の情報を取得

# タスクデータをファイルから読み込む関数
def load_tasks():
    global tasks
    try:
        with open(DATA_FILE, "r") as f:
            tasks = json.load(f)
    except FileNotFoundError:
        tasks = []

def print_task_info():
    for task in tasks:
        # 各タスクから必要な情報を取り出して表示
        task_duration = task.get("task_duration", "N/A")
        start_date = task.get("start_date", "N/A")
        end_date = task.get("end_date", "N/A")
        task_name = task.get("name", "N/A")
        
        # タスク情報をフォーマットして表示
        print(f"Task Name: {task_name}")
        print(f"Duration: {task_duration}")
        print(f"Start Date: {start_date}")
        print(f"End Date: {end_date}")
        print("-" * 40)


load_tasks()

print_task_info()
#追加する予定の分割

#条件設定

#既存のイベントとの比較　すでに予定があるところにはスキップ




