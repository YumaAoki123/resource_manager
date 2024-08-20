from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from tkcalendar import DateEntry
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import os.path
import sys
import pickle
from datetime import datetime, timedelta, timezone
import pytz
import uuid
import sqlite3
# タスクを保存するためのリスト
tasks = []

email = os.getenv('EMAIL')

# DATA_FILE = 'tasks.json'

# # タスクデータをファイルから読み込む関数
# def load_tasks():
#     global tasks
#     try:
#         with open(DATA_FILE, "r") as f:
#             tasks = json.load(f)
#     except FileNotFoundError:
#         tasks = []

SCOPES = ["https://www.googleapis.com/auth/calendar"]
TOKEN_PICKLE = 'token.pickle'

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
creds = get_credentials()
service = build('calendar', 'v3', credentials=creds)

# SQLiteデータベースに接続（ファイルが存在しない場合は作成されます）
conn = sqlite3.connect('resource_manager.db')
cursor = conn.cursor()

# テーブルを作成します（存在しない場合のみ）
cursor.execute('''
CREATE TABLE IF NOT EXISTS event_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_uuid TEXT NOT NULL,
    event_id TEXT NOT NULL,
    summary TEXT,
    start_time TEXT,
    end_time TEXT,
    FOREIGN KEY (task_uuid) REFERENCES task_conditions(task_uuid)
)
''')

# テーブルを作成します（存在しない場合のみ）
cursor.execute('''
CREATE TABLE IF NOT EXISTS task_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_uuid TEXT NOT NULL,
    task_name TEXT NOT NULL,
    task_duration INTEGER NOT NULL,
    start_date DATETIME NOT NULL,             
    end_date DATETIME NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS task_conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_uuid TEXT NOT NULL,
    selected_time_range TEXT,
    selected_priority INTEGER,
    min_duration INTEGER,
    FOREIGN KEY (task_uuid) REFERENCES task_info (task_uuid)
)
''')

# 接続を閉じます
conn.commit()
conn.close()

# # タスクデータをファイルに保存する関数
# def save_tasks():
#     with open(DATA_FILE, "w") as f:
#         json.dump(tasks, f)

# def load_tasks():
    # try:
    #     with open(DATA_FILE, "r") as f:
    #         tasks = json.load(f)
    # except FileNotFoundError:
    #     tasks = []

def load_tasks():
    conn = sqlite3.connect('resource_manager.db')
    cursor = conn.cursor()
    
    # タスク情報をデータベースから読み込む
    cursor.execute('SELECT task_uuid, task_name, task_duration, start_date, end_date FROM task_info')
    rows = cursor.fetchall()
    
    global tasks
    tasks = []
    
    for row in rows:
        task = {
            "task_uuid": row[0],
            "task_name": row[1],
            "task_duration": row[2],
            "start_date": row[3],
            "end_date": row[4]
        }
        tasks.append(task)
    
    conn.close()

# タスクの所要時間と期間内の空き時間を比較するための関数。待ち時間に読み込み中のアニメーション。
# class LoadingAnimation:
#     def __init__(self, master):
#         self.master = master
#         self.canvas = tk.Canvas(master, width=50, height=50, bg='white', highlightthickness=0)
#         self.canvas.place(relx=0.5, rely=0.4, anchor='center')
#         self.arc = self.canvas.create_arc(10, 10, 40, 40, start=0, extent=150, fill='blue', outline='blue')
#         self.angle = 0
#         self.running = False

#     def start(self):
#         if not self.running:
#             self.running = True
#             self._rotate()

#     def stop(self):
#         self.running = False
#         self.canvas.place_forget()  # アニメーションを非表示にする

#     def _rotate(self):
#         if self.running:
#             self.angle = (self.angle + 5) % 360
#             self.canvas.delete(self.arc)
#             self.arc = self.canvas.create_arc(10, 10, 40, 40, start=self.angle, extent=150, fill='blue', outline='blue')
#             self.master.after(50, self._rotate)  # 更新間隔を調整

# def compare_hours(free_hours, task_duration):
#     # Tkinterのウィンドウを作成
#     window = ctk.CTk()
#     window.title("時間比較結果")
#     window.geometry("300x150")  # ウィンドウサイズの設定
#     # アニメーションウィジェットの作成
#     loading_animation = LoadingAnimation(window)
#     loading_animation.start()

#     def show_result():
#         # 比較結果を判定し、ラベルのテキストと色を設定
#         if task_duration > free_hours:
#             shortage = task_duration - free_hours
#             message = f"時間が足りません\n不足時間: {shortage} 分"
#             label = ctk.CTkLabel(window, text=message, text_color="white", fg_color="red", font=("Arial", 12))
#         else:
#             message = "時間が足りています"
#             label = ctk.CTkLabel(window, text=message, text_color="white", fg_color="green", font=("Arial", 12))
        
#         label.pack(pady=20)
#         loading_animation.stop()  # アニメーションを停止

#     # デモのため、ここで少し待つ（実際には処理をここに入れる）
#     window.after(2000, show_result)  # 2秒後に結果を表示
    
#     window.mainloop()



# タスクを追加する関数
def add_task():
        task_name = task_entry.get()
        task_duration = float(task_duration_entry.get())
        start_date = cal_start.get_date()
        end_date = cal_end.get_date()
        # タスクに固有のIDを生成
        task_uuid = str(uuid.uuid4())
  
# もし元がdatetime.date型なら、datetime.datetime型に変換する
        start_date = datetime.combine(start_date, datetime.min.time())  # datetime.date -> datetime.datetime
        end_date = datetime.combine(end_date, datetime.min.time())  # datetime.date -> datetime.datetime

# タイムゾーンを日本時間に設定
        jst = pytz.timezone('Asia/Tokyo')
        start_date_jst = jst.localize(start_date)
        end_date_jst = jst.localize(end_date)

# ISO形式の文字列に変換
        start_date_iso = start_date_jst.isoformat()
        end_date_iso = end_date_jst.isoformat()

        task_info = {
        "task_uuid": task_uuid,
        "task_name": task_name,
        "task_duration": task_duration,
        "start_date": start_date_iso,  # ISO形式の文字列に変換された日付
        "end_date": end_date_iso,
    }
        print(f"Adding task: {task_info}")  # デバッグ用の出力

        # Append the task dictionary to the task list
        tasks.append(task_info)
        update_task_listbox()  # Update task listbox to reflect the new task
        task_entry.delete(0, ctk.END)  # Clear the task entry field
        save_task_info(task_uuid, task_name, task_duration, start_date, end_date)  # Save the updated task list to a file or database

def save_task_info(task_uuid, task_name, task_duration, start_date, end_date):
        # SQLiteデータベースに接続
        conn = sqlite3.connect('resource_manager.db')
        cursor = conn.cursor()

        # UUIDとイベントIDのマッピングをデータベースに挿入
        cursor.execute('''
        INSERT INTO task_info (task_uuid, task_name, task_duration, start_date, end_date) VALUES (?, ?, ?, ?, ?)
        ''', (task_uuid, task_name, task_duration, start_date, end_date))

        # 変更を保存して接続を閉じます
        conn.commit()
        conn.close()

def update_task_listbox():
    task_listbox.delete(0, ctk.END)
    for task in tasks:
        print(f"Current task: {task}")  # デバッグ用の出力
        task_listbox.insert(ctk.END, f"{task['task_name']}")
    
def get_event_ids_by_uuid(uuid):
    """指定されたUUIDに関連するすべてのイベントIDを取得します。"""
    event_ids = []
    try:
        # SQLiteデータベースに接続
        conn = sqlite3.connect('resource_manager.db')
        cursor = conn.cursor()
        
        # UUIDに基づくイベントIDの取得
        cursor.execute("SELECT event_id FROM event_mappings WHERE task_uuid = ?", (uuid,))
        event_ids = [row[0] for row in cursor.fetchall()]
        
        conn.close()
    except sqlite3.Error as e:
        print(f"データベースエラー: {e}")
    
    return event_ids

def delete_selected_task():
    selected_task_index = task_listbox.curselection()
    if selected_task_index:
        index = selected_task_index[0]  # 選択されたタスクのインデックス
        task_uuid = tasks[index]['task_uuid']  # UUIDを取得
        calendar_id = email  # カレンダーIDを設定
        
        # UUIDに基づいて関連するイベントIDを取得
        event_ids = get_event_ids_by_uuid(task_uuid)
        
        if not event_ids:
            print("UUIDに関連するイベントIDが見つかりませんでした。")
            return

        # Googleカレンダーのイベントを削除
        delete_successful = True
        for event_id in event_ids:
            if not delete_google_calendar_event(service, event_id):
                delete_successful = False

        if delete_successful:
            # タスクをリストから削除
            del tasks[index]
            # データベースからUUIDに関連するイベントIDを削除
            delete_event_ids_by_uuid(task_uuid)

            # データベースから該当するタスクを削除
            delete_task_info_by_uuid(task_uuid)
           
            # リストボックスを更新
            update_task_delete_listbox()

            
            
        else:
            print("Googleカレンダーのイベント削除に失敗しました。")
    else:
        print("削除するタスクを選択してください。")

#一連のdelete関連のトランザクションを後で実装する
def delete_event_ids_by_uuid(uuid):
    """指定されたUUIDに関連するすべてのイベントIDをデータベースから削除します。"""
    try:
        # SQLiteデータベースに接続
        conn = sqlite3.connect('resource_manager.db')
        cursor = conn.cursor()

        # UUIDに基づくイベントIDの削除
        cursor.execute("DELETE FROM event_mappings WHERE task_uuid = ?", (uuid,))
        conn.commit()
        print(f"UUID {uuid} に関連するイベントIDがデータベースから削除されました。")

        conn.close()
    except sqlite3.Error as e:
        print(f"データベースエラー: {e}")

def delete_task_info_by_uuid(task_uuid):
    # データベースに接続
    conn = sqlite3.connect('resource_manager.db')
    cursor = conn.cursor()

    # `task_info`テーブルからUUIDに関連するタスクを削除
    cursor.execute('''
    DELETE FROM task_info WHERE task_uuid = ?
    ''', (task_uuid,))
    
    # 変更を保存して接続を閉じる
    conn.commit()
    conn.close()

def delete_google_calendar_event(service, event_id):
    try:
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        print(f"イベント {event_id} が削除されました。")
        return True
    except Exception as e:
        error_details = e.resp.get('content', '') if e.resp else '詳細情報なし'
        print(f"イベントの削除中にエラーが発生しました: {e}")
        print(f"エラー詳細: {error_details}")
        return False



# タスクリストを更新する関数
def update_task_delete_listbox():
    task_listbox.delete(0, ctk.END)
    for task in tasks:
        task_listbox.insert(ctk.END, f"{task['task_name']}")

# タスクリストボックスを更新する関数


# def create_label(window, text, fg_color):
#     label = tk.Label(window, text=text, fg=fg_color, font=("Arial", 12))
#     label.grid(pady=10)
#     return label

# タスク詳細を表示する関数
def show_task_details(event):
    # 選択されたタスクのインデックスを取得
    selected_index = task_listbox.curselection()
    if selected_index:
        index = selected_index[0]
        task = tasks[index]
        
        # ラベルにタスク詳細を表示
        details_text = f"タスク名: {task['task_name']}\n" \
                       f"タスクID: {task['task_uuid']}\n" \
                       f"所要時間: {task['task_duration']} 分\n" \
                       f"開始日: {task['start_date']}\n" \
                       f"終了日: {task['end_date']}\n"

        details_label.configure(text=details_text)
        update_progress_bar()

        
def get_free_times(start_time, end_time, calendar_id="primary"):
    
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
        start_time_jst = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(jst)
        end_time_jst = datetime.fromisoformat(end.replace("Z", "+00:00")).astimezone(jst)
       

        busy_periods.append((start_time_jst, end_time_jst))

    # 予定のない時間帯を計算
    busy_periods.sort()  # 予定のある時間帯をソート
    current_start = start_time.astimezone(jst)
    if end_time.tzinfo is None:
        end_time = jst.localize(end_time)
    for busy_start, busy_end in busy_periods:
            # 確認用にタイムゾーンを比較
        print(f"Current Start: {current_start}, Type: {type(current_start)}, TZ Info: {current_start.tzinfo}")
        print(f"End Time: {end_time}, Type: {type(end_time)}, TZ Info: {end_time.tzinfo}")

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


# イベント作成ウィンドウを作成する関数
def create_event_window():
    # 新しいウィンドウを作成
    event_window = ctk.CTk()
    event_window.title("イベント作成")
    event_window.geometry("800x500")

        # ウィンドウ全体にグリッドを設定
    event_window.grid_columnconfigure(0, weight=1)  # 左カラム
    event_window.grid_columnconfigure(1, weight=3)  # 右カラムを大きくする
    event_window.grid_rowconfigure(0, weight=1)
    event_window.grid_rowconfigure(1, weight=1)


    selected_index = task_listbox.curselection()
    if selected_index:
        index = selected_index[0]
        task = tasks[index]

    # タスク詳細をイベント情報として表示
    event_details_text = f"イベント名: {task['task_name']}\n" \
                         f"タスクID: {task['task_uuid']}\n" \
                         f"予定時間: {task['task_duration']} 分\n" \
                         f"開始日: {task['start_date']}\n" \
                         f"終了日: {task['end_date']}\n"
    
    event_details_label = ctk.CTkLabel(event_window, text=event_details_text, justify="left")
    event_details_label.grid(row=0, pady=20, padx=20)

    def get_selected_min_duration():
    # Entryの値を取得し、整数に変換
        min_duration = min_duration_entry.get()
        if min_duration.isdigit():
            print(f"取得した最小空き時間: {min_duration} 分")
            return int(min_duration)
        else:
            print("無効な入力です。整数値を入力してください。")
            return None
        

    min_duration_label = ctk.CTkLabel(event_window, text="最小空き時間 (分):")
    min_duration_label.grid(row=7, column=0, padx=10, pady=5)

    min_duration_entry = ctk.CTkEntry(event_window)
    min_duration_entry.grid(row=7, column=1, padx=10, pady=5)
    min_duration_entry.insert(0, "30")  # デフォルト値を設定

    def get_selected_priority_label():
        # 現在選択されているラジオボタンの値を取得
        selected_value = priority_var.get()

        # ラベルに応じたGoogleカレンダーのcolorIdを返す
        if selected_value == "1":
            return 11  # 優先度高
        elif selected_value == "2":
            return 2  # 優先度中
        elif selected_value == "3":
            return 7  # 優先度低

    def on_priority_change():
        # 優先度が変更されたときの処理
        selected_color_id = get_selected_priority_label()
        print(f"Selected Priority Color ID: {selected_color_id}")



    # 優先度選択ラジオボタンの変数
    priority_var = ctk.StringVar(value="2")  # デフォルトは中

    # 優先度選択ラジオボタンの作成
    priority_label = ctk.CTkLabel(event_window, text="優先度を選択:")
    priority_label.grid(row=6, column=0, padx=10, pady=5)

    priority_high = ctk.CTkRadioButton(event_window, text="高", variable=priority_var, value="1", command=on_priority_change)
    priority_high.grid(row=6, column=1, padx=10, pady=5)

    priority_medium = ctk.CTkRadioButton(event_window, text="中", variable=priority_var, value="2", command=on_priority_change)
    priority_medium.grid(row=6, column=2, padx=10, pady=5)

    priority_low = ctk.CTkRadioButton(event_window, text="低", variable=priority_var, value="3", command=on_priority_change)
    priority_low.grid(row=6, column=3, padx=10, pady=5)


    def get_selected_time_ranges():
        # 選択された時間範囲を取得
        time_ranges = []
        for start_combobox, end_combobox in time_range_comboboxes:
            start_time = start_combobox.get()
            end_time = end_combobox.get()
            if start_time != "指定しない" and end_time != "指定しない":
                time_ranges.append((start_time, end_time))

        # 選択された時間範囲を表示
        for start, end in time_ranges:
            print(f"指定時間帯: {start} - {end}")
        
        return time_ranges

    # 時刻リストを作成 (1時間ごと) + "指定しない" オプション
    time_options = ["指定しない"] + [f"{hour:02d}:00" for hour in range(24)]

    # タスクを埋め込んでいい時間帯のコンボボックス
    time_range_comboboxes = []

    def add_time_range():
        row_index = len(time_range_comboboxes) + 1

        # 時間帯ラベル
        range_label = ttk.Label(event_window, text=f"時間帯 {row_index}")
        range_label.grid(row=1+row_index, column=0, padx=10, pady=5)

        # 開始時間のコンボボックス
        start_combobox = ttk.Combobox(event_window, values=time_options)
        start_combobox.grid(row=1+row_index, column=1, padx=10, pady=5)
        start_combobox.current(0)

        # 終了時間のコンボボックス
        end_combobox = ttk.Combobox(event_window, values=time_options)
        end_combobox.grid(row=1+row_index, column=2, padx=10, pady=5)
        end_combobox.current(0)

        time_range_comboboxes.append((start_combobox, end_combobox))

    # 初期の時間範囲を追加
    add_time_range()

    # 時間範囲を追加するボタン
    add_range_button = ttk.Button(event_window, text="時間範囲を追加", command=add_time_range)
    add_range_button.grid(row=5, column=0, columnspan=3, pady=10)



    # 文字列をdatetimeオブジェクトに変換
    start_time = datetime.fromisoformat(task['start_date'])
    end_time = datetime.fromisoformat(task['end_date'])
    print(f"Start Time: {start_time}, tzinfo: {start_time.tzinfo}")
    print(f"End Time: {end_time}, tzinfo: {end_time.tzinfo}")
    print(f"Request Body: {start_time}")  # デバッグ用
    # 空き時間を取得
    free_times = get_free_times(start_time, end_time)

        #空き時間を表示（または他の処理に利用）
    # free_times_text = "空き時間:\n" + "\n".join(
    #     [f"開始: {start} 終了: {end}" for start, end in free_times]
    # )
    # free_times_label = ctk.CTkLabel(event_window, text=free_times_text, justify="left")
    # free_times_label.grid(pady=20, padx=20)



        # タイムゾーンを設定
    jst = pytz.timezone('Asia/Tokyo')

    # 選択された時間帯を毎日の範囲に合わせて日付を補完
    def combine_time_with_date(time_str, base_date):
        time = datetime.strptime(time_str, "%H:%M").time()
        naive_datetime = datetime.combine(base_date, time)
        return jst.localize(naive_datetime)
    
    # 選択された時間帯と空いている時間帯の重なりを計算
    def compare_time_ranges(selected_ranges, free_times, min_duration):
        task_times = []
        min_duration = get_selected_min_duration()
        
 # min_durationをtimedeltaに変換
        min_duration_td = timedelta(minutes=min_duration)
        # 各選択された時間帯について処理
        for free_start, free_end in free_times:
            # 空いている時間の開始日を基準日として使用
            current_date = free_start.date()
            next_date = current_date + timedelta(days=1)

            for selected_start_str, selected_end_str in selected_ranges:
                # 現在の日付と次の日付で選択された時間帯を補完
                selected_start_today = combine_time_with_date(selected_start_str, current_date)
                selected_end_today = combine_time_with_date(selected_end_str, current_date)

                # 翌日の選択された時間帯を補完
                selected_start_tomorrow = combine_time_with_date(selected_start_str, next_date)
                selected_end_tomorrow = combine_time_with_date(selected_end_str, next_date)

                # 今日の日付での重なりを確認
                if selected_start_today < free_end and selected_end_today > free_start:
                    task_start = max(selected_start_today, free_start)
                    task_end = min(selected_end_today, free_end)
                    if task_end - task_start >= min_duration_td:
                       task_times.append((task_start, task_end))

                # 翌日の日付での重なりを確認
                if selected_start_tomorrow < free_end and selected_end_tomorrow > free_start:
                    task_start = max(selected_start_tomorrow, free_start)
                    task_end = min(selected_end_tomorrow, free_end)
                    if task_end - task_start >= min_duration_td:
                       task_times.append((task_start, task_end))

        return task_times
    
   

    # def show_available_task_times():
    #     selected_ranges = get_selected_time_ranges()
    #     # ここで free_times を取得
    #     free_times = get_free_times(start_time, end_time, calendar_id=email)
    #     min_duration = get_selected_min_duration()
    #     available_task_times = compare_time_ranges(selected_ranges, free_times, min_duration)

    #             # 結果を出力
    #     for task_start, task_end in available_task_times:
    #         print(f"タスクを実行可能な時間帯: {task_start} から {task_end}")

    def check_available_time(task_times, task_duration_minutes):
            # タスクの所要時間を timedelta に変換
            task_duration_minutes = task['task_duration']
            task_duration = timedelta(minutes=task_duration_minutes)

            # 空いている時間帯の合計時間を計算
            total_available_time = timedelta()
            for start, end in task_times:
                total_available_time += end - start
            
            # 時間が足りるかどうかを確認
            if total_available_time >= task_duration:
                print(f"時間が足りてます")
            else:
                time_needed = task_duration - total_available_time
                print(f"時間が足りません。{time_needed} が不足しています")

    def calculate_percentage(task_duration, total_free_time):
        return (task_duration / total_free_time) * 100

    def format_duration(minutes):
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m"

    def update_graph(ax, task_duration_percentage, total_free_time_formatted, task_duration_formatted, time_difference_formatted, time_difference):
    # グラフをクリア
        ax.clear()

        # タイトルとラベルを再設定
        ax.set_title('Task vs. Free Time')
        ax.set_ylabel('Free Time (%)')

        # パーセントに基づいて色を選択
        bar_color = 'green' if task_duration_percentage <= 100 else 'red'

        # 空き時間とタスク時間を描画
        ax.bar(['Free'], [100], color='lightgray', edgecolor='black', label=f'Free: {total_free_time_formatted}')  # 空き時間の背景
        ax.bar(['Task'], [task_duration_percentage], color=bar_color, edgecolor='black', label=f'Task: {task_duration_formatted}')  # タスク時間のバー

       
            # 差分を示す点線を追加
        if task_duration_percentage > 100:
            ax.axhline(y=100, color='gray', linestyle='--', linewidth=1)
            ax.text(0.5, 100 + 1, f'-{time_difference_formatted}', color='red', ha='center', va='bottom')
        else:
            ax.axhline(y=task_duration_percentage, color='gray', linestyle='--', linewidth=1)
            ax.text(0.5, task_duration_percentage + 1, f'+{time_difference_formatted}', color='green', ha='center', va='bottom')
            
        ax.set_ylim(0, max(100, task_duration_percentage + 10))  # y軸の範囲を設定
        ax.legend(loc='upper right')

    def on_check_button_click():
        # ボタンがクリックされたときに呼ばれる関数
        task_duration_minutes = task['task_duration']
        selected_ranges = get_selected_time_ranges()
        min_duration = get_selected_min_duration()
        task_times = compare_time_ranges(selected_ranges, free_times, min_duration)

        # 空き時間の合計を計算
        total_free_time_minutes = sum((end - start).total_seconds() / 60 for start, end in task_times)
        total_free_time_formatted = format_duration(total_free_time_minutes)

        # タスク時間をパーセンテージに変換
        task_duration_percentage = calculate_percentage(task_duration_minutes, total_free_time_minutes)
        task_duration_formatted = format_duration(task_duration_minutes)

        # 差分を計算
        time_difference = total_free_time_minutes - task_duration_minutes
        time_difference_formatted = format_duration(abs(time_difference))

        # グラフを更新
        update_graph(ax, task_duration_percentage, total_free_time_formatted, task_duration_formatted, time_difference_formatted, time_difference)
        canvas.draw()

        result = check_available_time(task_times, task_duration_minutes)
        print(result)



    # 初期状態のFigureを作成
    fig, ax = plt.subplots(figsize=(3, 5))  # 縦棒グラフのためにサイズを調整
    ax.set_title('Task vs. Free Time')
    ax.set_ylabel('Free Time (%)')

    # Figureをキャンバスに埋め込む
    canvas = FigureCanvasTkAgg(fig, master=event_window)
    canvas.draw()
    canvas.get_tk_widget().grid(row=0, column=4, columnspan=3, padx=20, pady=10)  # ボタンの右側にグラフを表示

    # 時間の差を表示するラベルを作成（初期は空）
    difference_label = ctk.CTkLabel(event_window, text="")
    difference_label.grid(row=11, column=1, padx=20, pady=5)

    # 選択した時間範囲を取得するボタン
    select_button = ctk.CTkButton(event_window, text="空き時間検索", command=on_check_button_click)
    select_button.grid(row=9, column=0, pady=20)


    def add_events_to_google_calendar(service, task_times, task_name, task_uuid, selected_time_range, selected_priority, min_duration):
        """Google Calendarに複数のイベントを追加し、同じUUIDでイベントIDをマッピングします。"""
        # タスク条件を保存
        save_task_conditions(task_uuid, selected_time_range, selected_priority, min_duration)
        for start_time, end_time in task_times:
            event = {
                'summary': task_name,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Asia/Tokyo',
                },
                'colorId': str(selected_priority),  # イベントの色を設定
            }
            try:
                event_result = service.events().insert(calendarId="primary", body=event).execute()
                event_id = event_result.get('id')
                event_summary = event_result.get('summary')
                event_start = event_result['start'].get('dateTime', event_result['start'].get('date'))
                event_end = event_result['end'].get('dateTime', event_result['end'].get('date'))
                 # UUIDとイベントIDおよび詳細をデータベースに保存
                save_uuid_event_id_mapping(task_uuid, event_id, event_summary, event_start, event_end)
                print(f"Event created: {event_result['htmlLink']}")
                print(f"Event details saved: {event_summary}, {event_start} - {event_end}")
            except HttpError as error:
                print(f'An error occurred: {error}')

    def save_uuid_event_id_mapping(uuid, event_id, event_summary, event_start, event_end):
        # SQLiteデータベースに接続
        conn = sqlite3.connect('resource_manager.db')
        cursor = conn.cursor()

        # 新しいカラムに対応してデータを挿入
        cursor.execute('''
        INSERT INTO event_mappings (task_uuid, event_id, summary, start_time, end_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (uuid, event_id, event_summary, event_start, event_end))

        # 変更を保存して接続を閉じます
        conn.commit()
        conn.close()

    def save_task_conditions(task_uuid, selected_time_range, selected_priority, min_duration):
        """タスクの条件をデータベースに保存します。"""
        conn = sqlite3.connect('resource_manager.db')
        cursor = conn.cursor()
        # selected_time_rangeを文字列形式に変換
        time_range_str = ', '.join([f"{start}-{end}" for start, end in selected_time_range])
    # 保存するデータの内容を表示
        print("Saving task conditions:")
        print(f"task_uuid: {task_uuid}")
        print(f"selected_time_range: {time_range_str}")
        print(f"selected_priority: {selected_priority}")
        print(f"min_duration: {min_duration}")
        # task_conditions テーブルにデータを挿入
        cursor.execute('''
            INSERT OR REPLACE INTO task_conditions (task_uuid, selected_time_range, selected_priority, min_duration)
            VALUES (?, ?, ?, ?)
        ''', (task_uuid, time_range_str, selected_priority, min_duration))

        conn.commit()
        conn.close()


    def fill_available_time(task_times, task_duration_minutes):
        task_duration_minutes = task['task_duration']
     
        """空き時間にタスクを埋め込む時間帯を決定します。"""
        task_duration = timedelta(minutes=task_duration_minutes)
        remaining_duration = task_duration
        filled_task_times = []
        
        for start, end in task_times:
            available_duration = end - start
            
            if remaining_duration <= timedelta(0):
                break
            
            if available_duration >= remaining_duration:
                # 空き時間にタスクを埋め込む
                filled_task_times.append((start, start + remaining_duration))
                remaining_duration -= available_duration
            else:
                # 部分的にタスクを埋め込む
                filled_task_times.append((start, end))
                remaining_duration -= available_duration
        
        if remaining_duration <= timedelta(0):
            return filled_task_times
        else:
            print(f"タスクを完了するための時間が不足しています: {remaining_duration.total_seconds() / 60:.2f} 分不足しています")
            return []          
        
    def on_insert_button_click():
        selected_time_ranges = get_selected_time_ranges()
        min_duration = get_selected_min_duration()
        task_times = compare_time_ranges(selected_time_ranges, free_times, min_duration)
        task_duration_minutes = task['task_duration']
        selected_priority = get_selected_priority_label()
       # 空いている時間帯と所要時間を比較し、タスクを埋め込む
        filled_task_times = fill_available_time(task_times, task_duration_minutes)
        if filled_task_times:
           add_events_to_google_calendar(service, filled_task_times, task['task_name'],task['task_uuid'], selected_time_ranges, selected_priority, min_duration)
    test_button = ctk.CTkButton(event_window, text="test", command=get_free_times)
    test_button.grid(row=12, pady=20)
 
    # Googleカレンダーに追加するボタン
    add_event_button = ctk.CTkButton(event_window, text="Googleカレンダーに追加", command=on_insert_button_click)
    add_event_button.grid(row=11, pady=20)

    event_window.mainloop()
    
def get_all_mappings():
    """SQLiteデータベースから全てのUUID、イベントID、サマリー、開始時間、終了時間のマッピングを取得して表示します。"""
    # SQLiteデータベースに接続
    conn = sqlite3.connect('resource_manager.db')
    cursor = conn.cursor()

    # テーブルからすべての行を選択
    cursor.execute('SELECT task_uuid, event_id, summary, start_time, end_time FROM event_mappings')
    rows = cursor.fetchall()

    # 取得したマッピングを表示
    for row in rows:
        task_uuid, event_id, summary, start_time, end_time = row
        print(f"UUID: {task_uuid}, Event ID: {event_id}, Summary: {summary}, Start Time: {start_time}, End Time: {end_time}")

    # 接続を閉じる
    conn.close()
def get_all_task_conditions():
    """SQLiteデータベースから全てのタスク条件（UUID、時間帯、優先度、最小時間）を取得して表示します。"""
    # SQLiteデータベースに接続
    conn = sqlite3.connect('resource_manager.db')
    cursor = conn.cursor()

    # task_conditions テーブルからすべての行を選択
    cursor.execute('SELECT task_uuid, selected_time_range, selected_priority, min_duration FROM task_conditions')
    rows = cursor.fetchall()

    # 取得したタスク条件を表示
    for row in rows:
        task_uuid, selected_time_range, selected_priority, min_duration = row
        print(f"UUID: {task_uuid}, Time Range: {selected_time_range}, Priority: {selected_priority}, Min Duration: {min_duration}")

    # 接続を閉じる
    conn.close()
# プログレスバーの進捗率を計算する関数
def calculate_progress(task_times, total_task_duration):
    # 現在の時間をUTCとして取得
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    current_time = datetime.now(tokyo_tz)
    print(f"current_time{current_time}")
    completed_duration = 0

    for start_time, end_time in task_times:
        # 現在の時間より前に終了したタスクの時間を加算
        if end_time < current_time:
            task_duration_segment = (end_time - start_time).total_seconds() / 60  # 分単位でタスクの時間を計算
            completed_duration += task_duration_segment

    # プログレスバー用に進捗率を計算
    if total_task_duration == 0:
        return 0  # タスクがない場合は進捗0%
    
    progress_percentage = (completed_duration / total_task_duration) * 100
    print(f"progress_percentage{progress_percentage}")
    print(f"completed_duration{completed_duration}")
    print(f"total_task_duration{total_task_duration}")
    return progress_percentage
    



def fetch_task_times_and_duration(task_uuid):
    # SQLiteデータベースに接続
    conn = sqlite3.connect('resource_manager.db')
    cursor = conn.cursor()

    # 現在の時間を取得（Asia/Tokyo タイムゾーンに設定）
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    current_time = datetime.now(tokyo_tz)
    print(f"current_time_fetch{current_time}")


    # task_uuidに基づいて、現在の時間より前のタスクの時間情報を取得
    cursor.execute('''
        SELECT start_time, end_time FROM event_mappings
        WHERE task_uuid = ? AND end_time < ?
    ''', (task_uuid, current_time.isoformat()))

    # 取得したデータをリストに格納
    task_times = []
    for row in cursor.fetchall():
        # SQLiteのdatetime文字列をPythonのdatetimeオブジェクトに変換
        start_time = datetime.fromisoformat(row[0]).astimezone(tokyo_tz)
        end_time = datetime.fromisoformat(row[1]).astimezone(tokyo_tz)
        task_times.append((start_time, end_time))

    # データベース接続を閉じる
    conn.close()

    return task_times

# GUIのセットアップ
app = ctk.CTk()
app.title("resource_manager")
app.geometry("900x600")

# Notebook（タブ）ウィジェットの作成
notebook = ttk.Notebook(app)
notebook.grid(row=0, column=0, sticky="nsew")

# ウィンドウの列と行の比率を設定
app.grid_columnconfigure(0, weight=1)
app.grid_rowconfigure(0, weight=1)


# タスク管理タブ
task_management_frame = ctk.CTkFrame(notebook)
notebook.add(task_management_frame, text="リソース計算")

# グリッドレイアウト設定
task_management_frame.grid_columnconfigure(0, weight=1)
task_management_frame.grid_columnconfigure(1, weight=2)
task_management_frame.grid_rowconfigure(4, weight=1)

# タスク入力欄と追加ボタン
task_name_label = ctk.CTkLabel(task_management_frame, text="Task Name:")
task_name_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
task_entry = ctk.CTkEntry(task_management_frame, width=50)
task_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
task_duration_label = ctk.CTkLabel(task_management_frame, text="Task Duration:")
task_duration_label.grid(row=0, column=2, padx=10, pady=5, sticky="w")
task_duration_entry = ctk.CTkEntry(task_management_frame, width=50)
task_duration_entry.grid(row=0, column=3, padx=10, pady=5, sticky="ew")

add_button = ctk.CTkButton(task_management_frame, text="Add Task", command=add_task)
add_button.grid(row=1, column=0, padx=10, pady=5, sticky="w")

cal_start_label = ctk.CTkLabel(task_management_frame, text="Select Start Date:")
cal_start_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

cal_start = DateEntry(task_management_frame, selectmode='day', year=2024, month=7, day=1, width=12, background='darkblue', foreground='white', borderwidth=2)
cal_start.grid(row=2, column=1, padx=10, pady=5, sticky="w")

cal_end_label = ctk.CTkLabel(task_management_frame, text="Select End Date:")
cal_end_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")

cal_end = DateEntry(task_management_frame, selectmode='day', year=2024, month=7, day=1, width=12, background='darkblue', foreground='white', borderwidth=2)
cal_end.grid(row=3, column=1, padx=10, pady=5, sticky="w")


# タスク一覧タブ
task_list_frame = ctk.CTkFrame(notebook)
notebook.add(task_list_frame, text="タスク一覧")

# ウィンドウ全体にグリッドを設定
task_list_frame.grid_columnconfigure(0, weight=1)  # 左カラム
task_list_frame.grid_columnconfigure(1, weight=3)  # 右カラムを大きくする
task_list_frame.grid_rowconfigure(0, weight=1)
task_list_frame.grid_rowconfigure(1, weight=1)

task_listbox = tk.Listbox(task_list_frame, selectmode=tk.MULTIPLE, width=50, height=10)  
task_listbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

# ボタンの設定
delete_button = ctk.CTkButton(task_list_frame, text="タスク削除", command=delete_selected_task)
delete_button.grid(row=10, column=0, columnspan=3, pady=20)

# ボタンの設定
get_id_button = ctk.CTkButton(task_list_frame, text="タスク削除", command=get_all_mappings)
get_id_button.grid(row=11, column=0, columnspan=3, pady=20)

# イベント作成ウィンドウを開くボタン
create_event_button = ctk.CTkButton(task_list_frame, text="カレンダーに埋め込む", command=create_event_window)
create_event_button.grid(row=2, column=0, pady=5, sticky="ew")

# タスク詳細を表示するラベル
details_label = ctk.CTkLabel(
    task_list_frame,
    text="タスクの詳細をここに表示",
    font=("Arial", 25),
    anchor="w",
    justify="left",
    fg_color="white",
    corner_radius=5
)
details_label.grid(row=0, column=1, padx=10, pady=(10, 0), sticky="nsew")



# プログレスバーを更新する関数
def update_progress_bar():
    selected_task_index = task_listbox.curselection()
    
    if selected_task_index:
        # プログレスバーを0にリセット
        progress_bar.set(0)
        progress_label.configure(text="0% 完了")

        # 選択されたタスクのUUIDを取得
        index = selected_task_index[0]
        task_uuid = tasks[index]['task_uuid']  # 例としてtasksリストからUUIDを取得
        
        # 選択されたタスクのtask_durationも取得
        task_duration = tasks[index]['task_duration']  # 例としてtasksリストからtask_durationを取得

        # タスク時間を取得
        task_times = fetch_task_times_and_duration(task_uuid)

        # 進捗を計算
        progress_percentage = calculate_progress(task_times, task_duration)

        # 進捗率を0.0～1.0に変換
        target_progress = progress_percentage / 100

        # アニメーションで進捗バーを更新
        animate_progress_bar(target_progress)

    else:
        print("タスクが選択されていません。")

def animate_progress_bar(target_progress):
    current_progress = progress_bar.get()
    
    if current_progress < target_progress:
        # 進捗を増加させる
        current_progress += 0.01
        current_progress = min(current_progress, target_progress)  # 目標値を超えないように制限
        progress_bar.set(current_progress)
        
        # ラベルに進捗率を表示
        progress_label.configure(text=f"{int(current_progress * 100)}% 完了")
        
        # アニメーションを続ける
        task_list_frame.after(10, animate_progress_bar, target_progress)
    else:
        # 最終進捗率を表示
        progress_label.configure(text=f"{int(target_progress * 100)}% 完了")

# プログレスバーを作成
progress_bar = ctk.CTkProgressBar(task_list_frame, width=300, height=20, corner_radius=10, mode='determinate')
progress_bar.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky='ew')

# 進捗率を表示するラベル
progress_label = ctk.CTkLabel(task_list_frame, text="0%")
progress_label.grid(row=2, column=0, padx=10, pady=10)

# ユーザ情報管理タブ
user_information_frame = ctk.CTkFrame(notebook)
notebook.add(user_information_frame, text="ユーザ情報")

# ダブルクリックイベントのバインディング
task_listbox.bind('<Double-1>', show_task_details)

# タスクデータをロードして表示
load_tasks()
update_task_listbox()

# メインループの開始
app.mainloop()