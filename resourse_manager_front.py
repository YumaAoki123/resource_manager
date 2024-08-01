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

# タスクを保存するためのリスト
tasks = []
load_dotenv()

email = os.getenv('EMAIL')

SELECTED_PERIOD_FILE = 'selected_period.json'
DATA_FILE = 'tasks.json'

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
        # `selected_period.json`ファイルをロード
        try:
            with open(SELECTED_PERIOD_FILE, 'r') as f:
                selected_period_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            messagebox.showerror("Error", "Selected period data is missing or invalid.")
            return
        task_name = selected_period_data.get('task_name')
        task_duration = selected_period_data.get('task_duration')
        start_date = selected_period_data.get('start_date')
        end_date = selected_period_data.get('end_date')
        sleep_hours = selected_period_data.get('sleep_hours', 0)
        meal_hours = selected_period_data.get('meal_hours', 0)
        commute_hours = selected_period_data.get('commute_hours', 0)
        # Create a task dictionary with additional information
        task_info = {
            "name": task_name,
            "task_duration": task_duration,
            "start_date": start_date,
            "end_date": end_date,
            "sleep_hours": sleep_hours,
            "meal_hours": meal_hours,
            "commute_hours": commute_hours
        }

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
        task_listbox.insert(ctk.END, f"{task['name']}")

def create_label(window, text, fg_color):
    label = tk.Label(window, text=text, fg=fg_color, font=("Arial", 12))
    label.grid(pady=10)
    return label


# 選択した期間を取得して保存する関数
def on_save_selected_period():
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
        details_text = f"タスク名: {task['name']}\n" \
                       f"所要時間: {task['task_duration']} 分\n" \
                       f"開始日: {task['start_date']}\n" \
                       f"終了日: {task['end_date']}\n"

        details_label.configure(text=details_text)







# イベント作成ウィンドウを作成する関数
def create_event_window():
    # 新しいウィンドウを作成
    event_window = ctk.CTk()
    event_window.title("イベント作成")
    event_window.geometry("400x300")

    selected_index = task_listbox.curselection()
    if selected_index:
        index = selected_index[0]
        task = tasks[index]

    # タスク詳細をイベント情報として表示
    event_details_text = f"イベント名: {task['name']}\n" \
                         f"予定時間: {task['task_duration']} 分\n" \
                         f"開始日: {task['start_date']}\n" \
                         f"終了日: {task['end_date']}\n"
    

    event_details_label = ctk.CTkLabel(event_window, text=event_details_text, justify="left")
    event_details_label.grid(pady=20, padx=20)

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

    # Googleカレンダーに追加するボタン
    add_event_button = ctk.CTkButton(event_window, text="Googleカレンダーに追加")
    add_event_button.grid(pady=20)
       
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

search_button = ctk.CTkButton(task_management_frame, text="Save Selected Period", command=on_save_selected_period)
search_button.grid(row=4, column=0, padx=10, pady=5, sticky="w")

result_label = ctk.CTkLabel(task_management_frame, text="Free time: ")
result_label.grid(row=5, column=0, columnspan=2, pady=10, sticky="ew")

total_hours_label = ctk.CTkLabel(task_management_frame, text="Total hours: ")
total_hours_label.grid(row=6, column=0, columnspan=2, pady=10, sticky="ew")

# ユーザー入力用のテキストエリア
sleep_hours_label = ctk.CTkLabel(task_management_frame, text="Sleep Hours:")
sleep_hours_label.grid(row=7, column=0, padx=10, pady=5, sticky="w")
sleep_hours_entry = ctk.CTkEntry(task_management_frame)
sleep_hours_entry.grid(row=7, column=1, padx=10, pady=5, sticky="w")

meal_hours_label = ctk.CTkLabel(task_management_frame, text="Meal Hours:")
meal_hours_label.grid(row=8, column=0, padx=10, pady=5, sticky="w")
meal_hours_entry = ctk.CTkEntry(task_management_frame)
meal_hours_entry.grid(row=8, column=1, padx=10, pady=5, sticky="w")

commute_hours_label = ctk.CTkLabel(task_management_frame, text="Commute Hours:")
commute_hours_label.grid(row=9, column=0, padx=10, pady=5, sticky="w")
commute_hours_entry = ctk.CTkEntry(task_management_frame)
commute_hours_entry.grid(row=9, column=1, padx=10, pady=5, sticky="w")


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
create_event_button = ctk.CTkButton(task_list_frame, text="Create Event", command=create_event_window)
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