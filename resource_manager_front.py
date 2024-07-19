import tkinter as tk
from tkinter import messagebox, simpledialog
from tkcalendar import DateEntry
from tkinter import ttk
import json

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
        task_entry.delete(0, tk.END)
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

# 空いている時間を検索する関数
def find_free_time():
    start_date = cal_start.get_date()
    end_date = cal_end.get_date()

    if not start_date or not end_date:
        messagebox.showwarning("Warning", "Please select both start and end dates")
        return

    total_time = (end_date - start_date).total_seconds() / 60  # minutes
    occupied_time = sum(task['duration'] for task in tasks)
    free_time = total_time - occupied_time

    result_label.config(text=f"Free time: {free_time} minutes")

# タスクリストボックスを更新する関数
def update_task_listbox():
    task_listbox.delete(0, tk.END)
    for task in tasks:
        task_listbox.insert(tk.END, f"{task['name']} - {task['duration']} min")

# GUIのセットアップ
root = tk.Tk()
root.title("Task Manager")

# ウィンドウのサイズを設定 (幅x高さ)
root.geometry("900x600")

# Notebook（タブ）ウィジェットの作成
notebook = ttk.Notebook(root)
notebook.pack(pady=10, expand=True)

# タスク管理タブ
task_management_frame = ttk.Frame(notebook)
notebook.add(task_management_frame, text="Task Management")

# 開始日時と終了日時の入力欄
cal_start_label = tk.Label(task_management_frame, text="Select Start Date:")
cal_start_label.pack(pady=5)
cal_start = DateEntry(task_management_frame, selectmode='day', year=2024, month=7, day=1, width=12, background='darkblue', foreground='white', borderwidth=2)
cal_start.pack(pady=5)

cal_end_label = tk.Label(task_management_frame, text="Select End Date:")
cal_end_label.pack(pady=5)
cal_end = DateEntry(task_management_frame, selectmode='day', year=2024, month=7, day=1, width=12, background='darkblue', foreground='white', borderwidth=2)
cal_end.pack(pady=5)

search_button = tk.Button(task_management_frame, text="Find Free Time", command=find_free_time)
search_button.pack(pady=5)

result_label = tk.Label(task_management_frame, text="Free time: ")
result_label.pack(pady=10)

# タスク入力欄と追加ボタン
task_entry = tk.Entry(task_management_frame, width=50)
task_entry.pack(pady=10)
add_button = tk.Button(task_management_frame, text="Add Task", command=add_task)
add_button.pack(pady=5)

# タスク一覧タブ
task_list_frame = ttk.Frame(notebook)
notebook.add(task_list_frame, text="Task List")

task_listbox = tk.Listbox(task_list_frame, selectmode=tk.MULTIPLE, width=50, height=10)
task_listbox.pack(pady=10)

delete_button = tk.Button(task_list_frame, text="Delete Task", command=delete_task)
delete_button.pack(pady=5)

# タスクデータをロードして表示
load_tasks()
update_task_listbox()

root.mainloop()
