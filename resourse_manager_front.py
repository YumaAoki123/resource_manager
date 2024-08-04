from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from tkcalendar import DateEntry
import customtkinter as ctk
import json
from resource_manager import save_selected_period, process_period_data, get_free_times # バックエンドの関数をインポート
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta, timezone
import pytz
import math
# タスクを保存するためのリスト
tasks = []
load_dotenv()

email = os.getenv('EMAIL')

SELECTED_PERIOD_FILE = 'selected_period.json'
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

# タスクデータをファイルに保存する関数
def save_tasks():
    with open(DATA_FILE, "w") as f:
        json.dump(tasks, f)

# タスクデータをファイルから読み込む関数
def load_tasks():
    global tasks
    try:
        with open(DATA_FILE, "r") as f:
            tasks = json.load(f)
    except FileNotFoundError:
        tasks = []

# タスクの所要時間と期間内の空き時間を比較するための関数。待ち時間に読み込み中のアニメーション。
class LoadingAnimation:
    def __init__(self, master):
        self.master = master
        self.canvas = tk.Canvas(master, width=50, height=50, bg='white', highlightthickness=0)
        self.canvas.place(relx=0.5, rely=0.4, anchor='center')
        self.arc = self.canvas.create_arc(10, 10, 40, 40, start=0, extent=150, fill='blue', outline='blue')
        self.angle = 0
        self.running = False

    def start(self):
        if not self.running:
            self.running = True
            self._rotate()

    def stop(self):
        self.running = False
        self.canvas.place_forget()  # アニメーションを非表示にする

    def _rotate(self):
        if self.running:
            self.angle = (self.angle + 5) % 360
            self.canvas.delete(self.arc)
            self.arc = self.canvas.create_arc(10, 10, 40, 40, start=self.angle, extent=150, fill='blue', outline='blue')
            self.master.after(50, self._rotate)  # 更新間隔を調整

def compare_hours(free_hours, task_duration):
    # Tkinterのウィンドウを作成
    window = ctk.CTk()
    window.title("時間比較結果")
    window.geometry("300x150")  # ウィンドウサイズの設定
    # アニメーションウィジェットの作成
    loading_animation = LoadingAnimation(window)
    loading_animation.start()

    
    def show_result():
        # 比較結果を判定し、ラベルのテキストと色を設定
        if task_duration > free_hours:
            shortage = task_duration - free_hours
            message = f"時間が足りません\n不足時間: {shortage} 分"
            label = ctk.CTkLabel(window, text=message, text_color="white", fg_color="red", font=("Arial", 12))
        else:
            message = "時間が足りています"
            label = ctk.CTkLabel(window, text=message, text_color="white", fg_color="green", font=("Arial", 12))
        
        label.pack(pady=20)
        loading_animation.stop()  # アニメーションを停止

    # デモのため、ここで少し待つ（実際には処理をここに入れる）
    window.after(2000, show_result)  # 2秒後に結果を表示
    
    window.mainloop()



# タスクを追加する関数
def add_task():
        task_name = task_entry.get()
        task_duration = float(task_duration_entry.get())
        start_date = cal_start.get_date()
        end_date = cal_end.get_date()
  
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
        save_tasks()  # Save the updated task list to a file or database
    
        
# タスクを削除する関数
def delete_task():
    selected_indices = task_listbox.curselection()
    if not selected_indices:
        messagebox.showwarning("Warning", "No task selected")
        return

    for index in selected_indices[::-1]:
        task_listbox.delete(index)
        del tasks[index]
    save_tasks()

# タスクリストボックスを更新する関数
def update_task_listbox():
    task_listbox.delete(0, ctk.END)
    for task in tasks:
        print(f"Current task: {task}")  # デバッグ用の出力
        task_listbox.insert(ctk.END, f"{task['task_name']}")

def create_label(window, text, fg_color):
    label = tk.Label(window, text=text, fg=fg_color, font=("Arial", 12))
    label.grid(pady=10)
    return label


# 選択した期間を取得して保存する関数
#def on_save_selected_period():
    task_name = task_entry.get()
    task_duration = float(task_duration_entry.get())
    start_date = cal_start.get_date()
    end_date = cal_end.get_date()
    sleep_hours = float(sleep_hours_entry.get())
    meal_hours = float(meal_hours_entry.get())
    commute_hours = float(commute_hours_entry.get())
    save_selected_period(task_name, task_duration, start_date, end_date)
    print(f"Selected Start Date: {start_date}")
    print(f"Selected End Date: {end_date}")
    free_hours, total_duration_hours, sum_others, total_hours = process_period_data()
    result_label.configure(text=f"Free time: {free_hours} hours")
    total_hours_label.configure(text=f"total_hours: {total_hours} hours")
    sleep_hours_label.configure(text=f"sleep hours: {sleep_hours} hours")
    meal_hours_label.configure(text=f"sleep hours: {meal_hours} hours")
    commute_hours_label.configure(text=f"sleep hours: {commute_hours} hours")
    # バックエンドの関数を呼び出して期間を処理
    process_period_data()
    compare_hours(free_hours, task_duration)


# タスク詳細を表示する関数
def show_task_details(event):
    # 選択されたタスクのインデックスを取得
    selected_index = task_listbox.curselection()
    if selected_index:
        index = selected_index[0]
        task = tasks[index]
        
        # ラベルにタスク詳細を表示
        details_text = f"タスク名: {task['task_name']}\n" \
                       f"所要時間: {task['task_duration']} 分\n" \
                       f"開始日: {task['start_date']}\n" \
                       f"終了日: {task['end_date']}\n"

        details_label.configure(text=details_text)


# イベント作成ウィンドウを作成する関数
def create_event_window():
    # 新しいウィンドウを作成
    event_window = ctk.CTk()
    event_window.title("イベント作成")
    event_window.geometry("800x500")

    selected_index = task_listbox.curselection()
    if selected_index:
        index = selected_index[0]
        task = tasks[index]

    # タスク詳細をイベント情報として表示
    event_details_text = f"イベント名: {task['task_name']}\n" \
                         f"予定時間: {task['task_duration']} 分\n" \
                         f"開始日: {task['start_date']}\n" \
                         f"終了日: {task['end_date']}\n"
    

    event_details_label = ctk.CTkLabel(event_window, text=event_details_text, justify="left")
    event_details_label.grid(row=10, pady=20, padx=20)

    def get_selected_min_duration():
    # Entryの値を取得し、整数に変換
        min_duration = min_duration_entry.get()
        if min_duration.isdigit():
            print(f"取得した最小空き時間: {min_duration} 分")
            return int(min_duration)
        else:
            print("無効な入力です。整数値を入力してください。")
            return None
        

    min_duration_label = ttk.Label(event_window, text="最小空き時間 (分):")
    min_duration_label.grid(row=0, column=0, padx=10, pady=5)

    min_duration_entry = ttk.Entry(event_window)
    min_duration_entry.grid(row=0, column=1, padx=10, pady=5)
    min_duration_entry.insert(0, "30")  # デフォルト値を設定


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
        range_label.grid(row=row_index, column=0, padx=10, pady=5)

        # 開始時間のコンボボックス
        start_combobox = ttk.Combobox(event_window, values=time_options)
        start_combobox.grid(row=row_index, column=1, padx=10, pady=5)
        start_combobox.current(0)

        # 終了時間のコンボボックス
        end_combobox = ttk.Combobox(event_window, values=time_options)
        end_combobox.grid(row=row_index, column=2, padx=10, pady=5)
        end_combobox.current(0)

        time_range_comboboxes.append((start_combobox, end_combobox))

    # 初期の時間範囲を追加
    add_time_range()

    # 時間範囲を追加するボタン
    add_range_button = ttk.Button(event_window, text="時間範囲を追加", command=add_time_range)
    add_range_button.grid(row=7, column=0, columnspan=3, pady=10)



    # 文字列をdatetimeオブジェクトに変換
    start_time = datetime.fromisoformat(task['start_date'])
    end_time = datetime.fromisoformat(task['end_date'])
 
    print(f"Request Body: {start_time}")  # デバッグ用
    # 空き時間を取得
    free_times = get_free_times(start_time, end_time, calendar_id=email)

    # 空き時間を表示（または他の処理に利用）
    free_times_text = "空き時間:\n" + "\n".join(
        [f"開始: {start} 終了: {end}" for start, end in free_times]
    )
    free_times_label = ctk.CTkLabel(event_window, text=free_times_text, justify="left")
    free_times_label.grid(pady=20, padx=20)



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
    
   

    def show_available_task_times():
        selected_ranges = get_selected_time_ranges()
        # ここで free_times を取得
        free_times = get_free_times(start_time, end_time, calendar_id=email)
        min_duration = get_selected_min_duration()
        available_task_times = compare_time_ranges(selected_ranges, free_times, min_duration)

                # 結果を出力
        for task_start, task_end in available_task_times:
            print(f"タスクを実行可能な時間帯: {task_start} から {task_end}")

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
            
    def on_check_button_click():
        # ボタンがクリックされたときに呼ばれる関数
        task_duration_minutes = task['task_duration']
        selected_ranges = get_selected_time_ranges()
        min_duration = get_selected_min_duration
        task_times = compare_time_ranges(selected_ranges, free_times, min_duration)
        result = check_available_time(task_times, task_duration_minutes)
        print(result)
    # 選択した時間範囲を取得するボタン
    select_button = ttk.Button(event_window, text="条件の時間帯とマッチする空いている時間を抽出", command=show_available_task_times)
    select_button.grid(row=8, column=0, columnspan=3, pady=20)
      # 選択した時間範囲を取得するボタン
    select_button = ttk.Button(event_window, text="チェック", command=on_check_button_click)
    select_button.grid(row=9, column=0, columnspan=3, pady=20)

    def add_events_to_google_calendar(service, calendar_id, task_times, task_name, color_id='2'):
        """Google Calendarにイベントを追加します。"""
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
                  'colorId': color_id,  # イベントの色を設定
            }
            try:
                event_result = service.events().insert(calendarId=calendar_id, body=event).execute()
                print(f"Event created: {event_result['htmlLink']}")
            except HttpError as error:
                print(f'An error occurred: {error}')

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
        selected_ranges = get_selected_time_ranges()
        min_duration = get_selected_min_duration()
        task_times = compare_time_ranges(selected_ranges, free_times, min_duration)
        task_duration_minutes = task['task_duration']
        
       # 空いている時間帯と所要時間を比較し、タスクを埋め込む
        filled_task_times = fill_available_time(task_times, task_duration_minutes)
       
        calendar_id = email  # 使用するカレンダーID
        if filled_task_times:
         add_events_to_google_calendar(service, calendar_id, filled_task_times, task['task_name'])


    # Googleカレンダーに追加するボタン
    add_event_button = ctk.CTkButton(event_window, text="Googleカレンダーに追加", command=on_insert_button_click)
    add_event_button.grid(row=10, pady=20)
    # イベントをGoogle Calendarに追加
    
   
    event_window.mainloop()

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

# 開始日時と終了日時の入力欄
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

task_listbox = tk.Listbox(task_list_frame, selectmode=tk.MULTIPLE, width=50, height=10)  # ここを修正
task_listbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

delete_button = ctk.CTkButton(task_list_frame, text="Delete Task")
delete_button.grid(row=1, column=0, pady=5, sticky="ew")

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

# プログレスバーを表示するためのFigureとAxesを作成
fig, ax = plt.subplots(figsize=(5, 2))
canvas = FigureCanvasTkAgg(fig, master=task_list_frame)  # 描画領域をTkinterウィジェットに設定
canvas.get_tk_widget().grid(row=1, column=1, padx=10, pady=(0, 10), sticky="nsew")  # gridを使用して配置

def update_progress(progress):
    """進捗バーを更新する"""
    # グラフをクリア
    ax.clear()
    # プログレスバーを描画
    ax.barh(['Task Progress'], [progress], color='skyblue')
    ax.set_xlim(0, 100)  # x軸の範囲を0〜100に設定
    ax.set_xlabel('Progress (%)')  # x軸のラベルを設定
    ax.set_title('Task Progress')  # グラフのタイトルを設定
    canvas.draw()  # キャンバスを再描画

# 進捗を更新（例として50%を設定）
update_progress(50)

# タスク管理タブ
user_information_frame = ctk.CTkFrame(notebook)
notebook.add(user_information_frame, text="ユーザ情報")

# ダブルクリックイベントのバインディング
task_listbox.bind('<Double-1>', show_task_details)

# タスクデータをロードして表示
load_tasks()
update_task_listbox()

# メインループの開始
app.mainloop()