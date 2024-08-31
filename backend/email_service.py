from flask import Flask, request, jsonify
from dotenv import load_dotenv

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
from datetime import datetime, timedelta, date
import pytz
import uuid
import sqlite3
from google.oauth2.credentials import Credentials
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import message_from_bytes
import base64
from dotenv import load_dotenv

load_dotenv()


# 環境変数からメールアドレスを取得
fromemail = os.getenv('FROMEMAIL')

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly', 
    'https://www.googleapis.com/auth/gmail.send', 
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/forms.responses.readonly'
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

def get_gmail_service():
    creds = get_credentials()
    gmail_service = build('gmail', 'v1', credentials=creds)
    return gmail_service

# Google Forms API を使うための準備
def get_forms_service():
    creds = get_credentials()  # 既存のget_credentials()関数を使用して認証を行う
    forms_service = build('forms', 'v1', credentials=creds)
    return forms_service




def create_message(sender, to, subject, body):
    """メールを作成する"""
    message = MIMEMultipart('alternative')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # HTML部分の作成
    part = MIMEText(body, 'html')
    message.attach(part)

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}

def send_message(service, sender, to, subject, body):
    """メールを送信し、Message-ID を取得して保存する"""
    try:
        message = create_message(sender, to, subject, body)
        sent_message = service.users().messages().send(userId="me", body=message).execute()
        message_id = sent_message['id']
        
        # メールの詳細を取得して Message-ID を取得
        msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
        headers = msg['payload']['headers']
        
        # Message-ID または Message-Id を取得
        message_id_header = next((header['value'] for header in headers if header['name'] in ['Message-ID', 'Message-Id']), None)
        
        if message_id_header:
            print(f"送信されたメールのMessage-ID: {message_id_header}")
            
            # Message-ID をファイルに保存
            with open('sent_message_id.txt', 'w') as f:
                f.write(message_id_header)
        else:
            print("Message-IDが見つかりませんでした。")
        
        return message_id
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None


# def on_send_button_click(user_id, form_link):
#     # Gmailサービスを取得
#     service = get_gmail_service()

#     # HTML形式でタスクのチェックボックス付きメール本文を作成
#     body = '<p>達成できなかったタスクにチェックを付けて、メールを返信してください:</p>'
#     body += '<ul>'
    
#      # メール本文にフォームリンクを追加
#     body = f'<p>本日のタスク達成状況を以下のリンクから記入してください。</p><a href="{form_link}">Googleフォームリンク</a>'

#         # 環境変数からメールアドレスを取得
#     fromemail = os.getenv('FROMEMAIL')
#     toemail = get_user_email(user_id)  # ユーザーIDからメールアドレスを取得する関数
#     print(f"fromemail: {fromemail} toemail: {toemail}")

#     # メールを送信
#     sender = fromemail  # 送信者のメールアドレス
#     recipient = toemail  # 受信者のメールアドレス
#     subject = '本日のタスク達成状況'
#     send_message(service, sender, recipient, subject, body)
   
#     print("メールが送信されました")

# # ユーザーIDからメールアドレスを取得する関数
# def get_user_email(user_id):
#     conn = create_connection()
#     try:
#         cursor = conn.cursor()
#         cursor.execute("SELECT email FROM users WHERE id = ?", (user_id,))
#         result = cursor.fetchone()
#         if result:
#             return result[0]  # メールアドレスを返す
#         else:
#             raise ValueError("ユーザーIDが見つかりません")
#     except Exception as e:
#         print(f"Error retrieving email: {e}")
#         return None
#     finally:
#         conn.close()


#フォームの作成
def create_form(tasks):
    service = get_forms_service()
     # 今日のタスクを取得
    
# フォームを作成
    form = {
        "info": {
            "title": "今日のタスク達成状況",
        }
    }
    result = service.forms().create(body=form).execute()
    form_id = result['formId']
    
    # タスク項目を追加 (batchUpdate)
    requests = []
    for idx, task in enumerate(tasks):
        task_name = task[0]
        start_time = task[2]
        end_time = task[3]
        priority = task[8]
        
        question_title = f"{task_name} (開始: {start_time}, 終了: {end_time}, 優先度: {priority})"
        
        # チェックボックス形式の質問を追加
        requests.append({
            "createItem": {
                "item": {
                    "title": question_title,
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {
                                "type": "RADIO",
                                "options": [
                                    {"value": "達成"},
                                    {"value": "未達成"}
                                ]
                            }
                        }
                    }
                },
                "location": {
                    "index": idx
                }
            }
        })
       
    # フォームIDをテキストファイルに保存
    with open('forms_id.txt', 'w') as f:
        f.write(form_id)
  
    # バッチ更新リクエストを実行
    batch_update_request = {"requests": requests}
    service.forms().batchUpdate(formId=form_id, body=batch_update_request).execute()

    # フォームのリンクを返す
    form_link = f"https://docs.google.com/forms/d/{form_id}/viewform"
    return form_link


def get_form_responses():
    """
    Google Formsから全回答を取得して出力する関数

    Parameters:
    service_account_file (str): サービスアカウントのJSONキーのパス
    form_id (str): 取得するフォームのID
    """
    service = get_forms_service()
    try:
        # フォームIDをファイルから読み取る
        with open('forms_id.txt', 'r') as f:
            form_id = f.read().strip()
        
        # フォームの回答を取得
        response = service.forms().responses().list(formId=form_id).execute()
        responses = response.get('responses', [])

        # 回答を出力
        for response in responses:
            print("回答ID:", response.get('responseId'))
            print("作成時間:", response.get('createTime'))
            print("最終送信時間:", response.get('lastSubmittedTime'))
            print("回答者メール:", response.get('respondentEmail'))

            answers = response.get('answers', {})
            for question_id, answer in answers.items():
                print(f"質問ID: {question_id}")

                # テキスト回答の処理
                text_answers = answer.get('textAnswers')
                if text_answers:
                    print("テキスト回答:", text_answers.get('answers'))

                # ファイルアップロード回答の処理
                file_upload_answers = answer.get('fileUploadAnswers')
                if file_upload_answers:
                    print("ファイルアップロード回答:", file_upload_answers.get('answers'))

                # 追加の回答形式に応じた処理を追加できます。
            
            print("総スコア:", response.get('totalScore'))
            print("-" * 20)
    
    except FileNotFoundError:
        print(f"ファイルが見つかりません")
    except Exception as e:
        print(f"エラーが発生しました: {e}")


