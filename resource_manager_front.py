import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
from tkcalendar import DateEntry
import customtkinter as ctk
import json
from resource_manager import save_selected_period, process_period_data  # バックエンドの関数をインポート

# タスクを保存するためのリスト
tasks = []

# タスクデータをファイルに保存する関数
def save_tasks():
    with open("tasks.json", "w") as f:
        json.dump(tasks, f)

# タスクデータをファイルから読み込む関数
def load_tasks():
    global tasks
    try:
        with open("tasks.json", "r") as f:
            tasks = json.load(f)
    except FileNotFoundError:
        tasks = []

# タスクを追加する関数
def add_task():
    task_name = task_entry.get()
    if task_name:
        task_duration = simpledialog.askinteger("Task Duration", "Enter task duration in minutes:")
        tasks.append({"name": task_name, "duration": task_duration})
        update_task_listbox()
        task_entry.delete(0, ctk.END)
        save_tasks()
    else:
        messagebox.showwarning("Warning", "Task name cannot be empty")

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
        task_listbox.insert(ctk.END, f"{task['name']} - {task['duration']} min")


# 選択した期間を取得して保存する関数
def on_save_selected_period():
    start_date = cal_start.get_date()
    end_date = cal_end.get_date()
    sleep_hours = float(sleep_hours_entry.get())
    meal_hours = float(meal_hours_entry.get())
    commute_hours = float(commute_hours_entry.get())
    save_selected_period(start_date, end_date, sleep_hours, meal_hours, commute_hours)
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
cal_start_label = ctk.CTkLabel(task_management_frame, text="Select Start Date:")
cal_start_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

cal_start = DateEntry(task_management_frame, selectmode='day', year=2024, month=7, day=1, width=12, background='darkblue', foreground='white', borderwidth=2)
cal_start.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

cal_end_label = ctk.CTkLabel(task_management_frame, text="Select End Date:")
cal_end_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

cal_end = DateEntry(task_management_frame, selectmode='day', year=2024, month=7, day=1, width=12, background='darkblue', foreground='white', borderwidth=2)
cal_end.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

search_button = ctk.CTkButton(task_management_frame, text="Save Selected Period", command=on_save_selected_period)
search_button.grid(row=2, column=0, columnspan=2, pady=5, sticky="ew")

result_label = ctk.CTkLabel(task_management_frame, text="Free time: ")
result_label.grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")
total_hours_label = ctk.CTkLabel(task_management_frame, text="total hours: ")
total_hours_label.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")




# ユーザー入力用のテキストエリア
sleep_hours_label = ctk.CTkLabel(task_management_frame, text="Sleep Hours:")
sleep_hours_label.grid(row=6, column=0, padx=10, pady=5, sticky="w")
sleep_hours_entry = ctk.CTkEntry(task_management_frame)
sleep_hours_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

meal_hours_label = ctk.CTkLabel(task_management_frame, text="Meal Hours:")
meal_hours_label.grid(row=7, column=0, padx=10, pady=5, sticky="w")
meal_hours_entry = ctk.CTkEntry(task_management_frame)
meal_hours_entry.grid(row=7, column=1, padx=10, pady=5, sticky="ew")

commute_hours_label = ctk.CTkLabel(task_management_frame, text="Commute Hours:")
commute_hours_label.grid(row=8, column=0, padx=10, pady=5, sticky="w")
commute_hours_entry = ctk.CTkEntry(task_management_frame)
commute_hours_entry.grid(row=8, column=1, padx=10, pady=5, sticky="ew")

# タスク入力欄と追加ボタン
task_entry = ctk.CTkEntry(task_management_frame, width=50)
task_entry.grid(row=8, column=0, padx=10, pady=5, sticky="w")
add_button = ctk.CTkButton(task_management_frame, text="Add Task", command=add_task)
add_button.grid(row=9, column=0, padx=10, pady=5, sticky="w")


# タスク一覧タブ
task_list_frame = ctk.CTkFrame(notebook)
notebook.add(task_list_frame, text="タスク一覧")

task_listbox = tk.Listbox(task_list_frame, selectmode=tk.MULTIPLE, width=50, height=10)  # ここを修正
task_listbox.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

delete_button = ctk.CTkButton(task_list_frame, text="Delete Task", command=delete_task)
delete_button.grid(row=1, column=0, pady=5, sticky="ew")

# タスク管理タブ
user_information_frame = ctk.CTkFrame(notebook)
notebook.add(user_information_frame, text="ユーザ情報")

# タスクデータをロードして表示
load_tasks()
update_task_listbox()

app.mainloop()
