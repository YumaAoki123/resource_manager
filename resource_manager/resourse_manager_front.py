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
from datetime import datetime, timedelta, date, timezone
import pytz
import uuid
import sqlite3
from google.oauth2.credentials import Credentials
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import message_from_bytes
import base64
import re
import time
import threading
import requests
from dotenv import load_dotenv
import webbrowser
import json



load_dotenv()

# セッションを作成
session = requests.Session()

 # SQLiteデータベースに接続（ファイルが存在しない場合は作成されます）
conn = sqlite3.connect('resource_manager.db')
cursor = conn.cursor()

cursor.execute('''
               CREATE TABLE IF NOT EXISTS users(
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               username TEXT NOT NULL,
               password TEXT NOT NULL
               )
               ''')


# テーブルを作成します（存在しない場合のみ）
cursor.execute('''
CREATE TABLE IF NOT EXISTS task_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_uuid TEXT NOT NULL,
    task_name TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS task_conditions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_uuid TEXT NOT NULL,
    task_duration INTEGER NOT NULL,
    start_date DATETIME NOT NULL,
    end_date DATETIME NOT NULL,
    selected_time_range TEXT NOT NULL,
    selected_priority INTEGER,
    min_duration INTEGER,
    FOREIGN KEY (task_uuid) REFERENCES task_info(task_uuid)
)
''')

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

# 接続を閉じます
conn.commit()
conn.close()


# アプリケーションの初期化
ctk.set_appearance_mode("Dark")  # 外観モードの設定（"System", "Dark", "Light"）
ctk.set_default_color_theme("blue")  # カラーテーマの設定
# アプリケーションウィンドウの作成
app = ctk.CTk()
app.geometry("400x300")
app.title("title")

def open_title(app):

    # サインインボタンの作成
    signin_button = ctk.CTkButton(app, text="Sign In", command=open_signin_window)
    signin_button.grid(pady=20)

    # サインアップボタンの作成
    signup_button = ctk.CTkButton(app, text="Sign Up", command=open_signup_window)
    signup_button.grid(pady=20)


def open_signin_window():
    
    login_window = ctk.CTk()
    login_window.geometry("300x200")
    login_window.title("Login")
    
    username_label = ctk.CTkLabel(login_window, text="Username")
    username_label.grid(pady=5)
    username_entry = ctk.CTkEntry(login_window)
    username_entry.grid(pady=5)
    
    password_label = ctk.CTkLabel(login_window, text="Password")
    password_label.grid(pady=5)
    password_entry = ctk.CTkEntry(login_window, show='*')
    password_entry.grid(pady=5)
    
    remember_var = ctk.BooleanVar()
    remember_check = ctk.CTkCheckBox(login_window, text="Remember me", variable=remember_var)
    remember_check.grid(pady=5)
    
    login_button = ctk.CTkButton(login_window, text="Login", command=lambda: login_user(username_entry.get(), password_entry.get(),remember_var.get(), login_window, username_entry, password_entry))
    login_button.grid(pady=20)
    
    login_window.mainloop()

# バリデーション関数の作成
def validate_login_input(username, password, username_entry, password_entry):
    # 初期化: フィールドの背景色をクリア
    username_entry.configure(border_color='')
    password_entry.configure(border_color='')

    # 未入力チェック
    if not username:
        username_entry.configure(border_color="red")
        print("ユーザー名が入力されていません")
        return False  # バリデーション失敗

    if not password:
        password_entry.configure(border_color="red")
        print("パスワードが入力されていません")
        return False  # バリデーション失敗

    return True  # バリデーション成功

# ログイン処理
def login_user(username, password, remember_me, login_window, username_entry, password_entry):
    # 入力のバリデーションを実行し、成功した場合にのみログイン処理を行う
    if validate_login_input(username, password, username_entry, password_entry):
        try:

            login_data = {
                'username': username,
                'password': password
            }
            print(f'logindata: { login_data}')

            # サーバーにPOSTリクエストを送信
            response = requests.post(
                'http://127.0.0.1:5000/login', 
                json=login_data,  # タスク名を辞書形式で送信
            )
            
            if response.status_code == 200:
                print("ログイン成功")
                jwt_token = response.json().get('token')
                save_jwt(jwt_token)  # jwtを保存
                open_main_app()  # メインアプリケーションを開く    
                login_window.destroy()    

            elif response.status_code in [401, 404]:
                # ユーザー名またはパスワードが間違っている場合
                messagebox.showerror("Error", "ユーザー名またはパスワードが違います")

            else:
                messagebox.showerror("Error", f"ログインエラー: {response.status_code}")

        except requests.RequestException as e:
            messagebox.showerror("Error", f"リクエストエラー: {e}")

# サインアップウィンドウを開く
def open_signup_window():
    signup_window = ctk.CTkToplevel()
    signup_window.title("Sign Up")
    signup_window.geometry("300x300")

    username_entry = ctk.CTkEntry(signup_window, placeholder_text="username")
    username_entry.grid(pady=10)

    password_entry = ctk.CTkEntry(signup_window, placeholder_text="Password", show="*")
    password_entry.grid(pady=10)

    signup_button = ctk.CTkButton(signup_window, text="Sign Up with Email", command=lambda: register_user(username_entry.get(), password_entry.get(), signup_window, username_entry, password_entry))
    signup_button.grid(pady=10)


def start_app():
    """アプリ起動時に自動ログイン処理を試行し、画面を切り替える"""
    if auto_login():
        print("自動ログイン成功、メインアプリ画面を表示します")
        
        open_main_app()  # 自動ログイン成功時のメイン画面表示
        
    else:
        print('sessionの有効期限切れ、タイトル画面を表示します')
        open_title(app)  # 自動ログイン失敗時のログイン画面表示
  




def register_user(username, password, signup_window, username_entry, password_entry):
    if validate_login_input(username, password, username_entry, password_entry):
        # 正しいURLを指定
        register_url = 'http://127.0.0.1:5000/register'
        register_data = {
            'username': username,
            'password': password
        }
        
        try:
   
            response = requests.post(register_url, json=register_data)
            print(f'response: {response}')

            # レスポンスが成功した場合
            if response.status_code == 201:
                jwt_token = response.json().get('token')
                
                # クッキーをファイルに保存
                save_jwt(jwt_token)  # クッキーを保存
                open_main_app()
                signup_window.destroy()
            elif response.status_code == 409:
                print("エラー: ユーザー名が既に存在します")
                messagebox.showerror("Error", "別のユーザー名を使用してください。")
            else:
                print(f"エラー: {response.status_code}")
                messagebox.showerror("Error", f"登録エラー: {response.status_code}")
        except requests.RequestException as e:
            print(f"リクエストエラー: {e}")
            messagebox.showerror("Error", f"リクエストエラー: {e}")

def save_jwt(jwt_token):
    with open('jwt.json', 'w') as file:
        json.dump(jwt_token, file)

def load_jwt():
    if os.path.exists('jwt.json'):
        with open('jwt.json', 'r') as file:
            return json.load(file)
    return None

def auto_login():
    jwt = load_jwt()
    if jwt:      
        # HTTPヘッダーにJWTを含める
        headers = {
            'Authorization': f'Bearer {jwt}'
}
        # サーバーから条件のないタスクを取得
        response = requests.get('http://127.0.0.1:5000/auto_login', headers=headers
        )
        
        if response.status_code == 200:
            print("自動ログイン成功")
            return True
        else:
            print("自動ログイン失敗。再ログインが必要です。")
            return False
    else:
        print("クッキーが見つかりません。再ログインが必要です。")
        return False

def clear_window():
        """ウィンドウをクリアする"""
        for widget in app.winfo_children():
            widget.destroy()  # 現在のウィジェットをすべて削除




# メインアプリケーションの画面を開く
def open_main_app():

    # 認証に必要なスコープ
    SCOPES = [
        'https://www.googleapis.com/auth/calendar'
    ]

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
    def get_calendar_service():
        creds = get_credentials()
        calendar_service = build('calendar', 'v3', credentials=creds)
        return calendar_service
    
    def get_gmail_service():
        creds = get_credentials()
        gmail_service = build('gmail', 'v1', credentials=creds)
        return gmail_service

    # Google Forms API を使うための準備
    def get_forms_service():
        creds = get_credentials()  # 既存のget_credentials()関数を使用して認証を行う
        forms_service = build('forms', 'v1', credentials=creds)
        return forms_service




   

    def get_today_tasks():
        # データベースに接続
        conn = sqlite3.connect('resource_manager.db')
        cursor = conn.cursor()

        # 今日の日付を取得（ローカルタイムゾーン）
        today = datetime.now(pytz.timezone('Asia/Tokyo')).date()
        today_str = today.strftime('%Y-%m-%d')  # YYYY-MM-DD形式に変換

        # SQLクエリを実行して、今日の日付に一致する全ての詳細情報を取得
        cursor.execute('''
            SELECT ti.task_name, em.event_id, em.start_time, em.end_time, 
                tc.task_duration, tc.start_date, tc.end_date, 
                tc.selected_time_range, tc.selected_priority, tc.min_duration
            FROM event_mappings em
            JOIN task_info ti ON em.task_uuid = ti.task_uuid
            JOIN task_conditions tc ON em.task_uuid = tc.task_uuid
            WHERE strftime('%Y-%m-%d', datetime(em.start_time, 'localtime')) = ?
        ''', (today_str,))

        # 結果を取得
        tasks_details = cursor.fetchall()

        # 結果をループして表示
        for details in tasks_details:
            print(f"Task Name: {details[0]}, Event ID: {details[1]}, Start Time: {details[2]}, End Time: {details[3]}, "
                f"Task Duration: {details[4]}, Start Date: {details[5]}, End Date: {details[6]}, "
                f"Selected Time Range: {details[7]}, Selected Priority: {details[8]}, Min Duration: {details[9]}")

        # データベース接続を閉じる
        conn.close()
        
        # タスクの詳細情報を返す
        return tasks_details


    # def create_message(sender, to, subject, body):
    #     """メールを作成する"""
    #     message = MIMEMultipart('alternative')
    #     message['to'] = to
    #     message['from'] = sender
    #     message['subject'] = subject

    #     # HTML部分の作成
    #     part = MIMEText(body, 'html')
    #     message.attach(part)

    #     raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    #     return {'raw': raw_message}

    # def send_message(service, sender, to, subject, body):
    #     """メールを送信し、Message-ID を取得して保存する"""
    #     try:
    #         message = create_message(sender, to, subject, body)
    #         sent_message = service.users().messages().send(userId="me", body=message).execute()
    #         message_id = sent_message['id']
            
    #         # メールの詳細を取得して Message-ID を取得
    #         msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    #         headers = msg['payload']['headers']
            
    #         # Message-ID または Message-Id を取得
    #         message_id_header = next((header['value'] for header in headers if header['name'] in ['Message-ID', 'Message-Id']), None)
            
    #         if message_id_header:
    #             print(f"送信されたメールのMessage-ID: {message_id_header}")
                
    #             # Message-ID をファイルに保存
    #             with open('sent_message_id.txt', 'w') as f:
    #                 f.write(message_id_header)
    #         else:
    #             print("Message-IDが見つかりませんでした。")
            
    #         return message_id
    #     except Exception as e:
    #         print(f"エラーが発生しました: {e}")
    #         return None


    # def on_send_button_click():
    #     # Gmailサービスを取得
    #     service = get_gmail_service()
        
    #     form_link = create_form()

    #     # HTML形式でタスクのチェックボックス付きメール本文を作成
    #     body = '<p>達成できなかったタスクにチェックを付けて、メールを返信してください:</p>'
    #     body += '<ul>'
        
    #      # メール本文にフォームリンクを追加
    #     body = f'<p>本日のタスク達成状況を以下のリンクから記入してください。</p><a href="{form_link}">Googleフォームリンク</a>'

    #         # 環境変数からメールアドレスを取得
    #     fromemail = os.getenv('FROMEMAIL')
    #     toemail = os.getenv('TOEMAIL')
    #     print(f"fromemail: {fromemail} toemail: {toemail}")

    #     # メールを送信
    #     sender = fromemail  # 送信者のメールアドレス
    #     recipient = toemail  # 受信者のメールアドレス
    #     subject = '本日のタスク達成状況'
    #     send_message(service, sender, recipient, subject, body)
    
    #     print("メールが送信されました")


    def get_recent_messages(service, max_results=3):
        try:
            # メールリストを取得する
            results = service.users().messages().list(userId='me', maxResults=max_results, labelIds=['INBOX'], q='').execute()
            messages = results.get('messages', [])
            
            # メールの詳細を取得
            detailed_messages = []
            for message in messages:
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()
                detailed_messages.append({
                    'id': message['id'],
                    'snippet': msg.get('snippet', ''),
                    'headers': msg['payload']['headers']
                })
            return detailed_messages
        
        except Exception as e:
            print(f"メール取得エラー: {e}")
            return []

    def check_recent_messages():
        service = get_gmail_service()
        try:
            # 最新の3件のメールを取得
            messages = get_recent_messages(service, max_results=3)
            
            if not messages:
                print("メールが見つかりませんでした。")
                return

            # 各メールのIDと件名を表示し、返信メールかどうかを確認
            for message in messages:
                message_id = message['id']
                subject = next((header['value'] for header in message['headers'] if header['name'] == 'Subject'), 'No Subject')
                print(f"メールID: {message_id} 件名: {subject}")
                check_if_reply(service, message_id)
            # get_form_responses()
        except Exception as e:
            print(f"エラーが発生しました: {e}")

    def check_if_reply(service, message_id):
        try:
            # メールの詳細を取得
            msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
            headers = msg['payload']['headers']
            
            # In-Reply-To ヘッダーの確認
            in_reply_to = next((header['value'] for header in headers if header['name'] == 'In-Reply-To'), None)
            
            # 送信メールのMessage-IDをファイルから読み込む
            try:
                with open('sent_message_id.txt', 'r') as f:
                    sent_message_id = f.read().strip()
            except FileNotFoundError:
                print("送信メールのMessage-IDが保存されていません。")
                sent_message_id = None
            
            if in_reply_to:
                if in_reply_to == sent_message_id:
                    print(f"メールID: {message_id} は返信メールで、一致しました。")
                else:
                    print(f"メールID: {message_id} は返信メールですが、一致しませんでした。返信先のメッセージID: {in_reply_to}")
            else:
                print(f"メールID: {message_id} は返信メールではありません。")
        
        except Exception as e:
            print(f"エラーが発生しました: {e}")

    def on_check_button_click():
        # スレッドで check_recent_messages を実行
        threading.Thread(target=check_recent_messages).start()


    # フォームの作成
    # def create_form():
    #     service = get_forms_service()
    #      # 今日のタスクを取得
    #     tasks = get_today_tasks()
    # # フォームを作成
    #     form = {
    #         "info": {
    #             "title": "今日のタスク達成状況",
    #         }
    #     }
    #     result = service.forms().create(body=form).execute()
    #     form_id = result['formId']
        
    #     # タスク項目を追加 (batchUpdate)
    #     requests = []
    #     for idx, task in enumerate(tasks):
    #         task_name = task[0]
    #         start_time = task[2]
    #         end_time = task[3]
    #         priority = task[8]
            
    #         question_title = f"{task_name} (開始: {start_time}, 終了: {end_time}, 優先度: {priority})"
            
    #         # チェックボックス形式の質問を追加
    #         requests.append({
    #             "createItem": {
    #                 "item": {
    #                     "title": question_title,
    #                     "questionItem": {
    #                         "question": {
    #                             "required": True,
    #                             "choiceQuestion": {
    #                                 "type": "RADIO",
    #                                 "options": [
    #                                     {"value": "達成"},
    #                                     {"value": "未達成"}
    #                                 ]
    #                             }
    #                         }
    #                     }
    #                 },
    #                 "location": {
    #                     "index": idx
    #                 }
    #             }
    #         })
        
    #     # フォームIDをテキストファイルに保存
    #     with open('forms_id.txt', 'w') as f:
    #         f.write(form_id)
    
    #     # バッチ更新リクエストを実行
    #     batch_update_request = {"requests": requests}
    #     service.forms().batchUpdate(formId=form_id, body=batch_update_request).execute()

    #     # フォームのリンクを返す
    #     form_link = f"https://docs.google.com/forms/d/{form_id}/viewform"
    #     return form_link


    # def get_form_responses():
    #     """
    #     Google Formsから全回答を取得して出力する関数

    #     Parameters:
    #     service_account_file (str): サービスアカウントのJSONキーのパス
    #     form_id (str): 取得するフォームのID
    #     """
    #     service = get_forms_service()
    #     try:
    #         # フォームIDをファイルから読み取る
    #         with open('forms_id.txt', 'r') as f:
    #             form_id = f.read().strip()
            
    #         # フォームの回答を取得
    #         response = service.forms().responses().list(formId=form_id).execute()
    #         responses = response.get('responses', [])

    #         # 回答を出力
    #         for response in responses:
    #             print("回答ID:", response.get('responseId'))
    #             print("作成時間:", response.get('createTime'))
    #             print("最終送信時間:", response.get('lastSubmittedTime'))
    #             print("回答者メール:", response.get('respondentEmail'))

    #             answers = response.get('answers', {})
    #             for question_id, answer in answers.items():
    #                 print(f"質問ID: {question_id}")

    #                 # テキスト回答の処理
    #                 text_answers = answer.get('textAnswers')
    #                 if text_answers:
    #                     print("テキスト回答:", text_answers.get('answers'))

    #                 # ファイルアップロード回答の処理
    #                 file_upload_answers = answer.get('fileUploadAnswers')
    #                 if file_upload_answers:
    #                     print("ファイルアップロード回答:", file_upload_answers.get('answers'))

    #                 # 追加の回答形式に応じた処理を追加できます。
                
    #             print("総スコア:", response.get('totalScore'))
    #             print("-" * 20)
        
    #     except FileNotFoundError:
    #         print(f"ファイルが見つかりません")
    #     except Exception as e:
    #         print(f"エラーが発生しました: {e}")

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


    def add_task():
        task_name = task_entry.get()
        
        if not task_name:
            print("タスク名を入力してください")
            return

        # サーバーへのリクエスト
        try:
            # セッションIDを読み込む（JWTトークン）
            jwt = load_jwt()
            
            # HTTPヘッダーにJWTを含める
            headers = {
                'Authorization': f'Bearer {jwt}'
            }

            # タスク名を含むJSONデータを準備
            data = {
                'task_name': task_name
            }

            # サーバーにPOSTリクエストを送信
            response = requests.post(
                'http://127.0.0.1:5000/add_task', 
                json=data,  # タスク名を辞書形式で送信
                headers=headers
            )
            
            # ステータスコードが201（Created）なら成功
            if response.status_code == 201:
                print("タスクが追加されました")
                update_todo_listbox(todo_listbox)  # タスクリストの更新
                task_entry.delete(0, ctk.END)  # 入力フィールドをクリア
            else:
                print(f"エラー: {response.json().get('error')}")
        
        except requests.RequestException as e:
            print(f"リクエストエラー: {e}")



    class ScheduleManager:
        def __init__(self, db_path='resource_manager.db'):
            self.db_path = db_path
            self.tasks = []
            self.schedules = []

        def _connect(self):
            return sqlite3.connect(self.db_path)

        def load_tasks(self):
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT task_uuid, task_name FROM task_info')
                rows = cursor.fetchall()
                
                self.tasks = []
                for row in rows:
                    task = {
                        "task_uuid": row[0],
                        "task_name": row[1],
                    }
                    self.tasks.append(task)
            finally:
                conn.close()

        def load_schedules(self):
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT task_uuid, task_duration, start_date, end_date FROM task_conditions')
                rows = cursor.fetchall()
                
                self.schedules = []
                for row in rows:
                    schedule = {
                        "task_uuid": row[0],
                        "task_duration": row[1],
                        "start_date": row[2],
                        "end_date": row[3]
                    }
                    self.schedules.append(schedule)
            finally:
                conn.close()


        def get_schedules(self):
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT ti.task_name, tc.task_uuid, tc.task_duration, tc.start_date, tc.end_date, tc.selected_time_range, tc.selected_priority, tc.min_duration
                    FROM task_info ti
                    JOIN task_conditions tc ON ti.task_uuid = tc.task_uuid
                ''')
                schedules = cursor.fetchall()
            finally:
                conn.close()
            return schedules
        
        def get_event_ids_by_uuid(self, task_uuid):
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT event_id, start_time, end_time
                    FROM event_mappings
                    WHERE task_uuid = ?
                ''', (task_uuid,))
                rows = cursor.fetchall()
                
                # event_id のリストを生成
                event_ids = [row[0] for row in rows]
                
            finally:
                conn.close()
            
            return event_ids

        
    #debug
        def get_user(self):
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM users')
                users = cursor.fetchall()
            finally:
                conn.close()
            return users
        def get_task_info(self):
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_info')
                tasks = cursor.fetchall()
            finally:
                conn.close()
            return tasks

        def get_task_conditions(self):
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM task_conditions')
                conditions = cursor.fetchall()
            finally:
                conn.close()
            return conditions

        def get_event_mappings(self):
            conn = self._connect()
            try:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM event_mappings')
                mappings = cursor.fetchall()
            finally:
                conn.close()
            return mappings

    def show_table_contents(schedule_manager):
        # テーブルの内容を取得
        users = schedule_manager.get_user()
        task_info = schedule_manager.get_task_info()
        task_conditions = schedule_manager.get_task_conditions()
        event_mappings = schedule_manager.get_event_mappings()

        # 結果を表示
        print("users テーブルの内容:")
        for row in users:
            print(row)
            
        print("task_info テーブルの内容:")
        for row in task_info:
            print(row)

        print("\ntask_conditions テーブルの内容:")
        for row in task_conditions:
            print(row)

        print("\nevent_mappings テーブルの内容:")
        for row in event_mappings:
            print(row)



    def update_todo_listbox(todo_listbox):
        todo_listbox.delete(0, ctk.END)

        try:
         
            # セッションIDを読み込む
            jwt = load_jwt()
            
        # HTTPヘッダーにJWTを含める
            headers = {
                'Authorization': f'Bearer {jwt}'
}
            # サーバーから条件のないタスクを取得
            response = requests.get('http://127.0.0.1:5000/get_tasks_without_conditions', headers=headers)
           
            
            if response.status_code == 200:
                tasks = response.json()
                for task in tasks:
                    todo_listbox.insert(ctk.END, task['task_name'])
            else:
                print(f"エラー: {response.json().get('error')}")
        except requests.RequestException as e:
            print(f"リクエストエラー: {e}")


    def delete_todo_task(todo_listbox):
        selected_task_index = todo_listbox.curselection()
        
        if selected_task_index:
            try:
                jwt = load_jwt()           # セッションIDを読み込む
                       # HTTPヘッダーにJWTを含める
                headers = {
                           'Authorization': f'Bearer {jwt}'
                     }
        
                # サーバーから条件のないタスクを取得
                response = requests.get('http://127.0.0.1:5000/get_tasks_without_conditions',headers=headers)
                if response.status_code == 200:
                    tasks = response.json()
                    
                    # 選択されたタスクのインデックスを元に、tasksからタスクを取得
                    index = selected_task_index[0]
                    selected_task = tasks[index]
                    task_uuid = selected_task['task_uuid']  # 正しいキーでtask_uuidを取得
                    
                    # APIエンドポイントに対してDELETEリクエストを送信
                    delete_response = requests.delete('http://127.0.0.1:5000/delete_todo_task',
                                                      headers=headers,
                                                      json={"task_uuid": task_uuid})

                    if delete_response.status_code == 200:
                        print("Task deleted successfully!")
                        # リストボックスを更新
                        update_todo_listbox(todo_listbox)
                    else:
                        print(f"Failed to delete task: {delete_response.json().get('error')}")
                else:
                    print(f"エラー: {response.json().get('error')}")
            except requests.RequestException as e:
                print(f"リクエストエラー: {e}")
        else:
            print("削除するタスクを選択してください。")



    def update_schedule_listbox(schedule_listbox):
        schedule_listbox.delete(0, ctk.END)
        schedules = get_schedules()  # スケジュールを取得
        
        if schedules:  # スケジュールがある場合のみ処理
            for schedule in schedules:
                # 'task_name' というキーを使ってアクセスする
                schedule_listbox.insert(ctk.END, schedule['task_name'])
                print(f"Current task: {schedule['task_name']}")  # デバッグ用の出力
        else:
            print("スケジュールデータが存在しません。")

    def get_schedules():
        try:
            jwt = load_jwt()
            
            # HTTPヘッダーにJWTを含める
            headers = {
                'Authorization': f'Bearer {jwt}'
            }
            # サーバーから条件のないタスクを取得
            response = requests.get('http://127.0.0.1:5000/get_schedules', headers=headers)
        
            if response.status_code == 200:
                schedules = response.json()
                print(f"schedules: {schedules}")
                return schedules  # スケジュールリストを返す
                
            else:
                print(f"エラー: {response.json().get('error')}")
                return []
        except requests.RequestException as e:
            print(f"リクエストエラー: {e}")
            return []




    def delete_selected_task(schedule_manager, service):
        selected_task_index = schedule_listbox.curselection()
        
        if selected_task_index:
            index = selected_task_index[0]  # 選択されたタスクのインデックス
            schedules = schedule_manager.get_schedules()  # スケジュールを取得
            
            if 0 <= index < len(schedules):
                selected_schedule = schedules[index]
                task_uuid = selected_schedule[1]  # スケジュールから task_uuid を取得
                # UUIDに基づいて event_mappings テーブルからイベントIDを取得
                event_ids = schedule_manager.get_event_ids_by_uuid(task_uuid)

                if not event_ids:
                    print("UUIDに関連するイベントIDが見つかりませんでした")
                    return
                
                # Googleカレンダーのイベントを削除
                delete_successful = True
                for event_id in event_ids:
                    if not delete_google_calendar_event(service, event_id):
                        delete_successful = False

                if delete_successful:
                    # タスクをリストから削除
                    schedule_manager.delete_task_by_uuid(task_uuid)

                    # リストボックスを更新
                    update_task_delete_listbox(schedule_manager)
                    
                else:
                    print("Googleカレンダーのイベント削除に失敗しました。")
            else:
                print("無効なタスクが選択されました。")
        else:
            print("削除するタスクを選択してください。")


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



    def update_task_delete_listbox(schedule_manager):
        schedule_listbox.delete(0, ctk.END)
        schedules = schedule_manager.get_schedules()
        for schedule in schedules:
            print(f"Current task: {schedule[0]}")  # デバッグ用の出力
            schedule_listbox.insert(ctk.END, schedule[0])


    # タスクリストボックスを更新する関数


    # def create_label(window, text, fg_color):
    #     label = tk.Label(window, text=text, fg=fg_color, font=("Arial", 12))
    #     label.grid(pady=10)
    #     return label

    # タスク詳細を表示する関数


    def show_schedule_details(event):
        
        # 選択されたタスクのインデックスを取得
        selected_index = schedule_listbox.curselection()
        
        if selected_index:
            index = selected_index[0]
            
            # schedulesの更新と取得
            schedules = get_schedules()
            print("全スケジュール内容:", schedules)  # スケジュール内容を表示
            
            if index < len(schedules):  # インデックスが有効か確認
                schedule = schedules[index]  # 辞書を取得
                
                # 辞書のキーに基づいてデータを取得
                task_name = schedule['task_name']
                task_id = schedule['task_id']
                task_duration = schedule['task_duration']
                start_date = schedule['start_date']
                end_date = schedule['end_date']
                time_ranges = schedule['selected_time_range']
                
                # 優先度を判定し、表示内容を決定
                if schedule['selected_priority'] == 11:
                    selected_priority = "高"
                elif schedule['selected_priority'] == 2:
                    selected_priority = "中"
                elif schedule['selected_priority'] == 7:
                    selected_priority = "低"
                else:
                    selected_priority = str(schedule['selected_priority'])
                # 現在の時間を取得するために東京タイムゾーンを設定
                tokyo_tz = pytz.timezone('Asia/Tokyo')

              # 開始日・終了日を変換して日本時間で表示
                start_date_dt = datetime.strptime(start_date, "%a, %d %b %Y %H:%M:%S %Z")  # 文字列をdatetimeオブジェクトに変換
                end_date_dt = datetime.strptime(end_date, "%a, %d %b %Y %H:%M:%S %Z")  # 同様に変換

                # 日本時間に変換
                start_date_jp = start_date_dt.astimezone(tokyo_tz).strftime("%Y/%m/%d %H:%M")  # フォーマット指定: YYYY/MM/DD HH:MM
                end_date_jp = end_date_dt.astimezone(tokyo_tz).strftime("%Y/%m/%d %H:%M")  # 同様に変換
                # 開始日と終了日を1つにまとめる
                date_range = f"{start_date_jp} 〜 {end_date_jp}"

                # 詳細テキストを作成
                details_text = f"タスク名: {task_name}\n" \
                               f"スケジュール時間: {task_duration}\n" \
                               f"期間: {date_range}\n" \
                               f"時間帯: {time_ranges}\n" \
                               f"優先度: {selected_priority}\n"
                
                details_label.configure(text=details_text)
                update_progress_bar()  # プログレスバーを更新
            else:
                print("無効なインデックス:", index)
        else:
            print("スケジュールが選択されていません。")




    def create_event_window(todo_listbox):
        # 選択されたタスクのインデックスを取得
        selected_index = todo_listbox.curselection()
        
        if selected_index:
            index = selected_index[0]
            
            # サーバーから条件のないタスクを取得
            try:
                            # セッションIDを読み込む（JWTトークン）
                jwt = load_jwt()
                
                # HTTPヘッダーにJWTを含める
                headers = {
                    'Authorization': f'Bearer {jwt}'
                }

                # サーバーにPOSTリクエストを送信
                response = requests.get(
                    'http://127.0.0.1:5000/get_tasks_without_conditions', 
                    headers=headers
                )
                if response.status_code == 200:
                    tasks = response.json()  # タスクのリストを取得
                    
                    if 0 <= index < len(tasks):
                        selected_task = tasks[index]
                        task_id = selected_task['task_id']  # タスクUUID
                        task_name = selected_task['task_name']  # タスク名

                        # 選択されたタスクの名前とUUIDをスケジュールマネージャに保存
                        schedule_manager.selected_task_id = task_id
                        schedule_manager.selected_task_name = task_name

                        # イベント作成用の新しいウィンドウを作成
                        event_window = ctk.CTk()
                        event_window.title("イベント作成")
                        event_window.geometry("800x500")
                        
                        # タスク詳細をイベント情報として表示
                        event_details_text = f"イベント名: {task_name}\n"
                        event_window_label = ctk.CTkLabel(event_window, text=event_details_text)
                        event_window_label.grid(pady=10)
                        
                        # 他のウィジェットの作成やイベントの追加処理をここに記述
                        
                    else:
                        print("タスクのインデックスが不正です")
                else:
                    print(f"サーバーエラー: {response.json().get('error')}")
            except requests.RequestException as e:
                print(f"リクエストエラー: {e}")
        else:
            print("タスクを選択してください")


        def get_selected_min_duration():
        # Entryの値を取得し、整数に変換
            min_duration = min_duration_entry.get()
            if min_duration.isdigit():
                print(f"取得した最小空き時間: {min_duration} 分")
                return int(min_duration)
            else:
                print("無効な入力です。整数値を入力してください。")
                return None
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

        # 現在の日付を取得
        today = date.today()

        # ラベルの追加
        cal_range_label = ctk.CTkLabel(event_window, text="Select Date Range:")
        cal_range_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

        # 開始日付のDateEntry（デフォルトを今日に設定）
        cal_start = DateEntry(event_window, selectmode='day', year=today.year, month=today.month, day=today.day, width=12, background='darkblue', foreground='white', borderwidth=2)
        cal_start.grid(row=1, column=1, padx=10, pady=5, sticky="w")

        # 終了日付のDateEntry（デフォルトを今日に設定）
        cal_end = DateEntry(event_window, selectmode='day', year=today.year, month=today.month, day=today.day, width=12, background='darkblue', foreground='white', borderwidth=2)
        cal_end.grid(row=1, column=2, padx=10, pady=5, sticky="w")

        task_duration_label = ctk.CTkLabel(event_window, text="Task Duration:")
        task_duration_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
        task_duration_entry = ctk.CTkEntry(event_window, width=50)
        task_duration_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        min_duration_label = ctk.CTkLabel(event_window, text="最小空き時間 (分):")
        min_duration_label.grid(row=4, column=0, padx=10, pady=5)
        min_duration_entry = ctk.CTkEntry(event_window)
        min_duration_entry.grid(row=4, column=1, padx=10, pady=5)
        min_duration_entry.insert(0, "30")  # デフォルト値を設定

        # 優先度選択ラジオボタンの変数
        priority_var = ctk.StringVar(value="2")  # デフォルトは中
        # 優先度選択ラジオボタンの作成
        priority_label = ctk.CTkLabel(event_window, text="優先度を選択:")
        priority_label.grid(row=5, column=0, padx=10, pady=5)
        priority_high = ctk.CTkRadioButton(event_window, text="高", variable=priority_var, value="1", command=on_priority_change)
        priority_high.grid(row=5, column=1, padx=10, pady=5)
        priority_medium = ctk.CTkRadioButton(event_window, text="中", variable=priority_var, value="2", command=on_priority_change)
        priority_medium.grid(row=5, column=2, padx=10, pady=5)
        priority_low = ctk.CTkRadioButton(event_window, text="低", variable=priority_var, value="3", command=on_priority_change)
        priority_low.grid(row=5, column=3, padx=10, pady=5)



        def get_task_duration():
            """タスク所要時間を取得する関数"""
            task_duration = task_duration_entry.get()
            if task_duration.isdigit():
                print(f"取得したタスク所要時間: {task_duration} 分")
                return int(task_duration)
            else:
                print("無効な入力です。整数値を入力してください。")
                return None
            
        def get_date_range():
            """開始日と終了日を取得する関数"""
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
            # 日付の範囲を表示
            print(f"取得した日付範囲: 開始日 {start_date}, 終了日 {end_date}")
            
            return start_date_iso, end_date_iso

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
            range_label.grid(row=6+row_index, column=0, padx=10, pady=5)

            # 開始時間のコンボボックス
            start_combobox = ttk.Combobox(event_window, values=time_options)
            start_combobox.grid(row=6+row_index, column=1, padx=10, pady=5)
            start_combobox.current(0)

            # 終了時間のコンボボックス
            end_combobox = ttk.Combobox(event_window, values=time_options)
            end_combobox.grid(row=6+row_index, column=2, padx=10, pady=5)
            end_combobox.current(0)

            time_range_comboboxes.append((start_combobox, end_combobox))

        # 初期の時間範囲を追加
        add_time_range()

        # 時間範囲を追加するボタン
        add_range_button = ttk.Button(event_window, text="時間範囲を追加", command=add_time_range)
        add_range_button.grid(row=7, column=0, columnspan=3, pady=10)

        
            #空き時間を表示（または他の処理に利用）
        # free_times_text = "空き時間:\n" + "\n".join(
        #     [f"開始: {start} 終了: {end}" for start, end in free_times]
        # )
        # free_times_label = ctk.CTkLabel(event_window, text=free_times_text, justify="left")
        # free_times_label.grid(pady=20, padx=20)
        # 認証を開始する関数
                    # タイムゾーンを設定
        jst = pytz.timezone('Asia/Tokyo')
        # UTC形式で受け取ったデータをJSTに変換
# UTC形式で受け取った日時データをJSTに変換する関数
        def convert_utc_to_jst(utc_datetime_str):
            utc_datetime = datetime.strptime(utc_datetime_str, "%a, %d %b %Y %H:%M:%S %Z")
            utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
            return utc_datetime.astimezone(jst)
        def get_free_times():
            """
            デスクトップアプリからバックエンドに期間を送信し、空き時間を取得する。
            """
            start_date, end_date = get_date_range()
            jwt = load_jwt()
            
            # HTTPヘッダーにJWTを含める
            headers = {
                'Authorization': f'Bearer {jwt}'
            }
            data = {
                    "start_date": start_date,
                    "end_date": end_date,
                    "calendar_id": "primary"  # 必要に応じてカレンダーIDを変更
             }

            if jwt:
                
                try:
                # サーバーにPOSTリクエストを送信
                    response = requests.post(
                    'http://127.0.0.1:5000/get_free_times', 
                    json=data,
                    headers=headers
                )
                    if response.status_code == 200:
                        free_times = response.json().get('free_times')
                        print(f'Free times: {free_times}')
                                        # JSTに変換
                        free_times_jst = [(convert_utc_to_jst(start), convert_utc_to_jst(end)) for start, end in free_times]
                        print(f'Free times (JST): {free_times_jst}')
                        return free_times_jst
                    else:
                        print(f"Error: {response.json().get('error')}")
                        return None
                except requests.RequestException as e:
                    print(f"Request error: {e}")
                    return None
        # #GoogleCalendarの既存の予定情報を取得し、それ以外の空いている時間帯情報を作成。
        # def get_free_times(calendar_id="primary"):
        #     # 開始日と終了日を取得
        #     start_date, end_date = get_date_range()

        #     # 空き時間のリスト
        #     free_times = []

        #     # JST タイムゾーンを設定
        #     jst = pytz.timezone('Asia/Tokyo')

        #     # 文字列を datetime オブジェクトに変換
        #     start_date_datetime = datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S%z")
        #     end_date_datetime = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S%z")

        #     # UTC に変換
        #     start_time_utc = start_date_datetime.astimezone(pytz.UTC)
        #     end_time_utc = end_date_datetime.astimezone(pytz.UTC)

        #     # Freebusy リクエストのボディを作成
        #     request_body = {
        #         "timeMin": start_time_utc.isoformat(),
        #         "timeMax": end_time_utc.isoformat(),
        #         "timeZone": "Asia/Tokyo",  # レスポンスのタイムゾーン
        #         "items": [{"id": calendar_id}]
        #     }
        #     service = get_calendar_service()
        #     # Freebusy リクエストを送信
        #     freebusy_result = service.freebusy().query(body=request_body).execute()

        #     busy_times = freebusy_result['calendars'][calendar_id]['busy']

        #     # 予定のある時間帯を計算
        #     busy_periods = []
        #     for busy_period in busy_times:
        #         start = busy_period['start']
        #         end = busy_period['end']

        #         # 日本時間に変換
        #         start_time_jst = datetime.fromisoformat(start.replace("Z", "+00:00")).astimezone(jst)
        #         end_time_jst = datetime.fromisoformat(end.replace("Z", "+00:00")).astimezone(jst)

        #         busy_periods.append((start_time_jst, end_time_jst))

        #     # 予定のない時間帯を計算
        #     busy_periods.sort()  # 予定のある時間帯をソート
        #     current_start = start_date_datetime.astimezone(jst)

        #     for busy_start, busy_end in busy_periods:
        #         # 予定のある時間帯の間に空き時間があれば追加
        #         if busy_start > current_start:
        #             free_times.append((current_start, busy_start))
                
        #         # 空き時間の開始を更新
        #         current_start = max(current_start, busy_end)

        #     # 最後の空き時間を追加
        #     if current_start < end_date_datetime:
        #         free_times.append((current_start, end_date_datetime))

        #     # 空き時間を出力
        #     for free_start, free_end in free_times:
        #         print(f"空いている時間帯: start_time: {free_start} から end_time: {free_end}")

        #     return free_times



        # 選択された時間帯を毎日の範囲に合わせて日付を補完
        def combine_time_with_date(time_str, base_date):
            time = datetime.strptime(time_str, "%H:%M").time()
            naive_datetime = datetime.combine(base_date, time)
            return jst.localize(naive_datetime)
        

        
        # ユーザが設定した条件(時間帯・最低タスク時間)での実際のタスク予定時間
        def compare_time_ranges(selected_ranges, free_times, min_duration):
            task_times = []  # タスク時間を保持するリスト
            min_duration_td = timedelta(minutes=min_duration)  # 最低タスク時間を timedelta に変換

            # free_times と selected_ranges の重なりを確認
            for free_start, free_end in free_times:
                # 空いている時間の開始日を基準日として使用
                current_date = free_start.date()

                while current_date <= free_end.date():
                    for selected_start_str, selected_end_str in selected_ranges:
                        # current_date と selected_start_str, selected_end_str でタスク候補の時間帯を生成
                        selected_start = combine_time_with_date(selected_start_str, current_date)
                        selected_end = combine_time_with_date(selected_end_str, current_date)

                        print(f'selected_start: {selected_start}, selected_end: {selected_end}')

                        # 今日の日付での重なりを確認
                        if selected_start < free_end and selected_end > free_start:
                            task_start = max(selected_start, free_start)  # 開始時刻の重なり部分を確認
                            task_end = min(selected_end, free_end)  # 終了時刻の重なり部分を確認

                            # 重なり時間が最低タスク時間を満たすか確認
                            if task_end - task_start >= min_duration_td:
                                task_times.append((task_start, task_end))  # タスク時間をリストに追加

                    # 次の日に移動して再度同じ時間帯のチェックを行う
                    current_date += timedelta(days=1)

            return task_times  # 最終的なタスク時間を返す

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
            task_duration = timedelta(minutes=task_duration_minutes)
            
            # 空いている時間帯の合計時間を計算
            total_available_time = timedelta()
            print(f'total_available_time]{total_available_time}')

            for start, end in task_times:
                total_available_time += end - start
                print(f'start, end]{start, end}')
            # 時間が足りるかどうかを確認
            if total_available_time >= task_duration:
                extra_time = total_available_time - task_duration
                print(f"時間が足りています。余裕時間: {extra_time}")
            else:
                time_needed = task_duration - total_available_time
                print(f"時間が足りません。{time_needed} が不足しています")

        def calculate_percentage(task_duration, total_free_time):
            print(f"task_duration: {task_duration}, total_free_time: {total_free_time}")

            if task_duration is None:
                print("Error: task_duration is None")
                return 0
            if total_free_time is None or total_free_time == 0:
                print("Error: total_free_time is None or 0")
                return 0

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
            start_date, end_date = get_date_range()
            # 空き時間を取得
            free_times = get_free_times()
            # ボタンがクリックされたときに呼ばれる関数
            task_duration_minutes = get_task_duration()
            selected_ranges = get_selected_time_ranges()
            min_duration = get_selected_min_duration()
            task_times = compare_time_ranges(selected_ranges, free_times, min_duration)
            print(f'task_times:{task_times}')
            # 空き時間の合計を計算
            free_time_under_conditions = sum((end - start).total_seconds() / 60 for start, end in task_times)
            
            print(f'free_time_under_conditions:{free_time_under_conditions}')
            total_free_time_formatted = format_duration(free_time_under_conditions)

            # タスク時間をパーセンテージに変換
            task_duration_percentage = calculate_percentage(task_duration_minutes, free_time_under_conditions)
            task_duration_formatted = format_duration(task_duration_minutes)

            # 差分を計算
            time_difference = free_time_under_conditions - task_duration_minutes
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
        canvas.get_tk_widget().grid(row=13, column=0, columnspan=3, padx=20, pady=10)  # ボタンの右側にグラフを表示

        # 時間の差を表示するラベルを作成（初期は空）
        difference_label = ctk.CTkLabel(event_window, text="")
        difference_label.grid(row=11, column=0, padx=20, pady=5)

        # 選択した時間範囲を取得するボタン
        select_button = ctk.CTkButton(event_window, text="空き時間検索", command=on_check_button_click)
        select_button.grid(row=10, column=0, pady=20)

        def add_events_to_google_calendar(filled_task_times, task_name, task_uuid, task_duration, start_date, end_date, selected_time_range, selected_priority, min_duration):
            """Google Calendarに複数のイベントを追加し、タスク条件と一緒にサーバへ送信します。"""
            
            # selected_time_rangeを文字列形式に変換
            time_range_str = ', '.join([f"{start}-{end}" for start, end in selected_time_range])
            
            print(f'time_range_str:{time_range_str}')

            # イベントデータとタスク条件をまとめたデータ
            data = {
                'task_id': task_id,
                'task_duration': task_duration,
                'start_date': start_date,
                'end_date': end_date,
                'selected_time_range': time_range_str,
                'selected_priority': selected_priority,
                'min_duration': min_duration,
                'events': []
            }

            # イベントデータを追加
            for start_time, end_time in filled_task_times:
                event_data = {
                    'task_name': task_name,
                    'start_time': start_time.isoformat(),
                    'end_time': end_time.isoformat(),
                    'selected_priority': selected_priority,
                }
                data['events'].append(event_data)
            
            # サーバへのPOSTリクエスト
            url = 'http://127.0.0.1:5000/add_events_and_task_conditions'
            try:
                jwt = load_jwt()
                
            # HTTPヘッダーにJWTを含める
                headers = {
                    'Authorization': f'Bearer {jwt}'
    }
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    print("Task conditions and events successfully sent to server.")
                    print(f"Server response: {response.json()}")
                else:
                    print(f"Failed to save task conditions and events: {response.text}")
            except requests.RequestException as e:
                print(f"Request error: {e}")
    #     def save_event_to_server(task_uuid, event_id, event_summary, event_start, event_end):
    #         """サーバにUUIDとイベントIDおよび詳細を保存"""
    #         url = 'http://127.0.0.1:5000/save_event_mapping'
    #         data = {
    #             'task_uuid': task_uuid,
    #             'event_id': event_id,
    #             'event_summary': event_summary,
    #             'event_start': event_start,
    #             'event_end': event_end
    #         }

    #         try:
    #             jwt = load_jwt()
                
    #         # HTTPヘッダーにJWTを含める
    #             headers = {
    #                 'Authorization': f'Bearer {jwt}'
    # }
    #             response = requests.post(url, json=data, headers=headers)
    #             if response.status_code == 200:
    #                 print("Event details saved to server.")
    #             else:
    #                 print(f"Failed to save event: {response.text}")
    #         except requests.RequestException as e:
    #             print(f"Request error: {e}")


        def fill_available_time(task_times, task_duration_minutes):
            task_duration_minutes = get_task_duration()
        
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
        
            # 選択されたタスクの名前とUUIDがある場合のみ実行
            if schedule_manager.selected_task_name and schedule_manager.selected_task_id:
                free_times = get_free_times()
                task_duration = get_task_duration()
                start_date, end_date = get_date_range()
                selected_time_ranges = get_selected_time_ranges()
                min_duration = get_selected_min_duration()
                task_times = compare_time_ranges(selected_time_ranges, free_times, min_duration)

                selected_priority = get_selected_priority_label()

                # 空いている時間帯と所要時間を比較し、タスクを埋め込む
                filled_task_times = fill_available_time(task_times, task_duration)
                if filled_task_times:
                    add_events_to_google_calendar(
                       
                        filled_task_times,
                        schedule_manager.selected_task_name,
                        schedule_manager.selected_task_id,
                        task_duration,
                        start_date,
                        end_date,
                        selected_time_ranges,
                        selected_priority,
                        min_duration
                    )
                    update_todo_listbox(todo_listbox)
                    update_schedule_listbox(schedule_listbox)
            else:
                print("タスクが選択されていません")

    # Googleカレンダーに追加するボタン
        add_event_button = ctk.CTkButton(event_window, text="Googleカレンダーに追加", command=on_insert_button_click)
        add_event_button.grid(row=12, column=0, pady=20)

        test_button = ctk.CTkButton(event_window, text="test", command=get_free_times)
        test_button.grid(row=12, column=1, pady=20)
    
    

        event_window.mainloop()


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
        


    def get_event_mappings(task_id):
        try:
            jwt = load_jwt()
            
            # HTTPヘッダーにJWTを含める
            headers = {
                'Authorization': f'Bearer {jwt}'
            }
            data = {
                'task_id':task_id
            }
            # サーバーから条件のないタスクを取得
            response = requests.post('http://127.0.0.1:5000/get_event_mappings', json=data, headers=headers)
        
            if response.status_code == 200:
                event_mappings = response.json()
                print(f"event_mappings: {event_mappings}")
                return event_mappings  # スケジュールリストを返す
                
            else:
                print(f"エラー: {response.json().get('error')}")
                return []
        except requests.RequestException as e:
            print(f"リクエストエラー: {e}")
            return []

    def fetch_task_times_and_duration(task_id):
        # 現在の時間を取得（Asia/Tokyo タイムゾーンに設定）
        tokyo_tz = pytz.timezone('Asia/Tokyo')
        current_time = datetime.now(tokyo_tz)
        print(f"current_time_fetch{current_time}")
        event_mappings = get_event_mappings(task_id)
        # 取得したデータをリストに格納
        task_times = []
        for row in event_mappings:
            # RFC 2822 形式の日時文字列を解析
            start_time = datetime.strptime(row['start_time'], '%a, %d %b %Y %H:%M:%S %Z').astimezone(tokyo_tz)
            end_time = datetime.strptime(row['end_time'], '%a, %d %b %Y %H:%M:%S %Z').astimezone(tokyo_tz)
            task_times.append((start_time, end_time))

        return task_times


   # 既存の app ウィンドウを使って main_app 内容を表示する
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


    add_button = ctk.CTkButton(task_management_frame, text="Add Task", command=add_task)
    add_button.grid(row=1, column=0, padx=10, pady=5, sticky="w")

    todo_listbox = tk.Listbox(task_management_frame, selectmode=tk.MULTIPLE, width=50, height=10)  
    todo_listbox.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")

    delete_todo_button = ctk.CTkButton(task_management_frame, text="タスク削除", command=lambda: delete_todo_task(todo_listbox))
    delete_todo_button.grid(row=3, padx=20, pady=10)

    def on_create_event_button_click():
        create_event_window(todo_listbox)  # schedule_manager を渡す
    # イベント作成ウィンドウを開くボタン
    create_event_button = ctk.CTkButton(task_management_frame, text="カレンダーに埋め込む", command=on_create_event_button_click)
    create_event_button.grid(row=4, padx=20, pady=10)

    today_task_button = ctk.CTkButton(task_management_frame, text="今日のタスク", command=get_today_tasks)
    today_task_button.grid(row=5, padx=20, pady=10)



    # def send_tasks():
    #     # タスク情報を取得
    #     tasks = get_today_tasks()

    #     # サーバーに送信するデータを作成
    #     data = {
    #         'user_id': USER_ID,
    #         'tasks': tasks
    #     }

    #     # サーバーにPOSTリクエストを送信
    #     try:
    #         response = requests.post(SERVER_URL, json=data)
    #         if response.status_code == 200:
    #             send_result_label.configure(text="タスク情報が送信されました。")
    #         else:
    #             send_result_label.configure(text=f"タスク情報の送信に失敗しました: {response.json().get('error')}")
    #     except requests.RequestException as e:
    #         send_result_label.configure(text=f"リクエストエラー: {str(e)}")


    # # メール送信ボタンの作成
    # send_button = ctk.CTkButton(task_management_frame, text="メールを送信", command=send_tasks)
    # send_button.grid(row=6, padx=20, pady=10)

    # ラベルの設定
    send_result_label = ctk.CTkLabel(task_management_frame, text="")
    send_result_label.grid(row=7, padx=20, pady=10)
    # 「返信確認」ボタンを作成
    check_reply_button = ctk.CTkButton(app, text="返信確認", command=on_check_button_click)
    check_reply_button.grid(row=8, padx=20, pady=10)


    # スケジュール一覧タブ
    task_list_frame = ctk.CTkFrame(notebook)
    notebook.add(task_list_frame, text="スケジュール一覧")

    # ウィンドウ全体にグリッドを設定
    task_list_frame.grid_columnconfigure(0, weight=1)  # 左カラム
    task_list_frame.grid_columnconfigure(1, weight=3)  # 右カラムを大きくする
    task_list_frame.grid_rowconfigure(0, weight=1)
    task_list_frame.grid_rowconfigure(1, weight=1)

    # フォントのサイズを指定して、文字を大きく
    listbox_font = ("Helvetica", 11)
    # リストボックスを作成
    schedule_listbox = tk.Listbox(task_list_frame, selectmode=tk.MULTIPLE, width=60, height=15, font=listbox_font)  
    schedule_listbox.grid(row=2, column=0, padx=10, pady=10, sticky="nsew")
 
    # delete_button = ctk.CTkButton(task_list_frame, text="タスク削除", command=lambda: delete_selected_task(schedule_manager, service))
    # delete_button.grid(row=10, column=0, columnspan=3, pady=20)

    check_button = ctk.CTkButton(task_list_frame, text="チェック", command=lambda: show_table_contents(schedule_manager))
    check_button.grid(row=11, column=0, columnspan=3, pady=20)

   # タスク詳細を表示するラベル
    details_label = ctk.CTkLabel(
        task_list_frame,
        text="タスクの詳細をここに表示",
        font=("Arial", 25),
        anchor="w",
        justify="left",
        fg_color="white",
        corner_radius=5,
        width=400,   # 固定幅
        height=100   # 固定高さ
    )
    details_label.grid(row=0, column=1, padx=10, pady=(10, 0), sticky="nsew")




    # プログレスバーを更新する関数
    def update_progress_bar():
        selected_task_index = schedule_listbox.curselection()
        
        if selected_task_index:
            # プログレスバーを0にリセット
            progress_bar.set(0)
            progress_label.configure(text="0% 完了")

            # 選択されたタスクのインデックスを取得
            index = selected_task_index[0]
            schedules = get_schedules()  # schedule_manager からスケジュールを取得

            # 選択されたタスクのスケジュールを取得
            if 0 <= index < len(schedules):
                selected_schedule = schedules[index]

                # タスクのUUIDと所要時間を取得
                task_id = selected_schedule['task_id']  # `task_uuid`は2番目の要素
                task_duration = selected_schedule['task_duration']  # `task_duration`は3番目の要素

                # タスク時間を取得
                task_times = fetch_task_times_and_duration(task_id)

                # 進捗を計算
                progress_percentage = calculate_progress(task_times, task_duration)

                # 進捗率を0.0～1.0に変換
                target_progress = progress_percentage / 100

                # アニメーションで進捗バーを更新
                animate_progress_bar(target_progress)
            else:
                print("無効なタスクが選択されました。")
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

    # プログレスバーの上に進捗率を表示するラベルを設置
    progress_label = ctk.CTkLabel(task_list_frame, text="0%")
    progress_label.place(in_=progress_bar, relx=0.5, rely=0.5, anchor='center')  # プログレスバーの中央に配置


    def logout_user(cookies):
        logout_url = 'http://127.0.0.1:5000/logout'

        if not cookies:
            print("クッキーが存在しないため、ログアウト処理は行いません。")
            clear_window()
            open_title(app)
            return

        try:
            # セッションを使用してサーバーと通信
            session = requests.Session()
            session.cookies.update(cookies)  # ログイン時に取得したクッキーを設定

            response = session.post(logout_url)

            print(f'response: {response}')

            # ログアウトが成功した場合
            if response.status_code == 200:
                print("ログアウト成功")
                # クッキーの削除
                if os.path.exists('cookies.json'):
                    os.remove('cookies.json')
                    print("クッキーファイルを削除しました")
                
                clear_window()
                open_title(app)
            else:
                print(f"エラー: {response.status_code}")
        except requests.RequestException as e:
            print(f"リクエストエラー: {e}")

    # ユーザ情報管理タブ
    user_information_frame = ctk.CTkFrame(notebook)
    notebook.add(user_information_frame, text="ユーザ情報")

    jwt = load_jwt()
    
    logout_button = ctk.CTkButton(user_information_frame, text="ログアウト", command=lambda:logout_user(jwt))
    logout_button.grid(row=3, column=0, padx=10, pady=5, sticky="w")
    
    email_label = ctk.CTkLabel(user_information_frame, text="Email:")
    email_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
    email_entry = ctk.CTkEntry(user_information_frame, width=50)
    email_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

    def registar_email():
        email = email_entry.get()

        print(f'email:{email}')
        try:
            jwt = load_jwt()
            
            # HTTPヘッダーにJWTを含める
            headers = {
                'Authorization': f'Bearer {jwt}'
            }
            data = {
                'email':email
            }
            # サーバーから条件のないタスクを取得
            response = requests.post('http://127.0.0.1:5000/registar_email', json=data, headers=headers)
        
            if response.status_code == 200:
                event_mappings = response.json()
                print(f"event_mappings: {event_mappings}")
                return event_mappings  # スケジュールリストを返す
                
            else:
                print(f"エラー: {response.json().get('error')}")
                return []
        except requests.RequestException as e:
            print(f"リクエストエラー: {e}")
            return []
        
    email_registar_button = ctk.CTkButton(user_information_frame, text="Registar Email", command=registar_email)
    email_registar_button.grid(row=1, column=0, padx=10, pady=5, sticky="w")



    # ダブルクリックイベントのバインディング
    schedule_listbox.bind('<Double-1>', lambda event: show_schedule_details(event))


    # ScheduleManager のインスタンスを作成
    schedule_manager = ScheduleManager()


    # update_task_listbox に schedule_manager を渡して呼び出す
    update_todo_listbox(todo_listbox)

    update_schedule_listbox(schedule_listbox)

        # .envファイルの読み込み
    load_dotenv()

# アプリ起動時に自動ログイン処理を実行
start_app()
# メインループの開始
app.mainloop()