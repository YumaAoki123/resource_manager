from flask import Blueprint,Flask, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from email_service import create_form
from calendar_service import calculate_free_times, get_credentials, get_calendar_service
from dotenv import load_dotenv
from model.models import Base, User, db_session, TaskInfo, TaskConditions, EventMappings


from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import datetime
import pytz
# calendar_service.py
from googleapiclient.discovery import build

from datetime import datetime
import os
import os.path
import sys
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from requests_oauthlib import OAuth2Session
from flask import make_response
import flask_session
# クライアントIDとクライアントシークレットを環境変数から取得する
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # HTTPSを強制しないようにする（ローカル開発用）
client_id = os.environ['GOOGLE_CLIENT_ID']
client_secret = os.environ['GOOGLE_CLIENT_SECRET']
redirect_uri = "http://127.0.0.1:5000/callback"

# 認可のためのスコープ
scope = ["https://www.googleapis.com/auth/calendar.readonly"]

# Google OAuth 2.0エンドポイント
authorization_base_url = "https://accounts.google.com/o/oauth2/auth"
token_url = 'https://accounts.google.com/o/oauth2/token'

main = Blueprint('main', __name__)

# ホームエンドポイント
@main.route('/')
def home():

    return 'Welcome to the home page'


# ユーザー登録
@main.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    # パスワードをハッシュ化
    hashed_password = generate_password_hash(password)

    new_user = User(username=username, password=hashed_password)

    try:
        # データベースに新しいユーザーを追加
        db_session.add(new_user)
        db_session.commit()

        # ユーザー登録が成功したらクッキーを設定してセッションを開始
        session['username'] = username  # クッキーに保存するデータ
        return jsonify({"message": "User registered successfully!"}), 201
    except IntegrityError:
        db_session.rollback()
        return jsonify({"error": "Username already exists"}), 409

@main.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
     # デバッグログを追加して、入力されたユーザー名を確認
    print(f"Received username: {username}")
    user = db_session.query(User).filter_by(username=username).first()

    if user is None:
        # デバッグ用のメッセージを表示
        print("ユーザーがデータベースに存在しません")
        return jsonify({"error": "User not found"}), 404

    # デバッグログを追加して、ユーザーのパスワードハッシュを確認
    print(f"User found in DB: {user.username}, Password hash: {user.password}")

    if user and check_password_hash(user.password, password):
        session['username'] = username
        response = jsonify({"message": "Logged in successfully"})
        return response, 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

@main.route('/check_session', methods=['GET'])
def check_session():
    if 'username' in session:
        return jsonify({"message": "Logged in"}), 200
    else:
        return jsonify({"message": "Not logged in"}), 401
    
@main.route('/logout', methods=['POST'])
def logout():
    # セッションからユーザーが存在しているか確認
    if 'username' in session:
        print(f"Logging out user: {session['username']}")  # ログアウト時のユーザー名を確認
        session.pop('username', None)  # セッションからユーザー情報を削除
    else:
        print("セッションにユーザーが存在しません")
        
    response = jsonify({"message": "Logged out successfully"})
     
    # クッキーがセットされているかを確認してクッキーの削除
    if request.cookies.get('session'):
        print(f"クッキーを削除: {request.cookies.get('session')}")
        response.set_cookie('session', '', expires=0)  # クッキーの削除
    else:
        print("クッキーが存在しません")

    
    return response

@main.route('/add_task', methods=['POST'])
def add_task():
    data = request.json
    task_name = data.get('task_name')

    if not task_name:
        return jsonify({"error": "Task name is required"}), 400

    task_uuid = str(uuid.uuid4())

    try:
        new_task = TaskInfo(task_uuid=task_uuid, task_name=task_name)
        db_session.add(new_task)
        db_session.commit()
        return jsonify({"message": "Task added successfully", "task_uuid": task_uuid}), 201
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@main.route('/get_tasks_without_conditions', methods=['GET'])
def get_tasks_without_conditions():
   
    try:
        # LEFT JOIN を使用して条件がないタスクを取得
        tasks = db_session.query(TaskInfo).outerjoin(TaskConditions, TaskInfo.task_uuid == TaskConditions.task_uuid) \
            .filter(TaskConditions.task_uuid == None).all()

        # 必要なデータをリストに整形
        task_list = [{'task_uuid': task.task_uuid, 'task_name': task.task_name} for task in tasks]
        
        return jsonify(task_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@main.route('/delete_todo_task', methods=['DELETE'])
def delete_todo_task():
    data = request.get_json()
    task_uuid = data.get('task_uuid')

    if not task_uuid:
        return jsonify({"error": "task_uuid is required"}), 400

    try:
        # task_infoからタスクを削除
        task = db_session.query(TaskInfo).filter_by(task_uuid=task_uuid).first()

        if not task:
            return jsonify({"error": "Task not found"}), 404

        # 関連するtask_conditionsやevent_mappingsも削除する場合
        db_session.query(TaskConditions).filter_by(task_uuid=task_uuid).delete()
        db_session.query(EventMappings).filter_by(task_uuid=task_uuid).delete()

        # task_info自体を削除
        db_session.delete(task)
        db_session.commit()

        return jsonify({"message": "Task deleted successfully!"}), 200
    except Exception as e:
        db_session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db_session.close()

@main.route("/auth")
def authorize():
    google = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)
    authorization_url, state = google.authorization_url(authorization_base_url, access_type="offline")
                # セッションIDをデバッグ
    
    auth_session_id = request.cookies.get('session')
    print(f'auth_session_id ID from cookies: {auth_session_id}')
    session['state'] = state
    
        # ユーザー情報も取得（デバッグ用）
    username = session.get('username', None)
    print(f'Username from session: {username}')
    
    saved_state = session.get('state')
    print(f'saved_state: {saved_state}')
    # 認証URLをクライアントに返す
    
    return jsonify({'authorization_url': authorization_url})

@main.route("/callback")
def callback():
    try:

                # クエリパラメータまたはヘッダーからセッションIDを取得
        client_session_id = request.args.get('session_id', None)
        print(f'client_session_id: {client_session_id}')

                # セッションIDをデバッグ
        session_id = request.cookies.get('session')
        print(f'Session ID from cookies: {session_id}')
        username = session.get('username', None)
        print(f'Username from session: {username}')

        #     # stateのチェック
        # state_from_provider = request.args.get('state')
        # state_in_session = session.get('oauth_state', None)
        # print(f'state from auth: {state_from_provider}')
        # print(f'state in session: {state_in_session}')
            # トークン情報を表示
                # セッションから `state` を取得
        google = OAuth2Session(client_id, redirect_uri=redirect_uri)

        # トークンを取得
        google.fetch_token(token_url, authorization_response=request.url, client_secret=client_secret)
        token = google.token
        print(f'Token: {token}')

    
        return jsonify('response_data')

    except Exception as e:
        # エラーの詳細を出力
        print(f'Error during token fetching: {e}')
        return 'Authentication failed!', 400

@main.route("/favicon.ico")
def favicon():
    return '', 204

# クライアントからのリクエストを受け取って、指定の期間の空き時間を取得
@main.route("/get_free_times", methods=['POST'])
def get_free_times():
    get_credentials()
    get_calendar_service()

    data = request.json
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    calendar_id = data.get('calendar_id', 'primary')
    
    calculate_free_times(data)
    return jsonify('success')
        

# @main.route('/submit-tasks', methods=['POST'])
# def submit_tasks():
#     data = request.get_json()
    
#     user_id = data.get('user_id')
#     tasks = data.get('tasks')

#     if not user_id or not tasks:
#         return jsonify({"error": "ユーザIDとタスク情報が必要です"}), 400
    
#     # ここでタスク情報をフォームに追加するために必要な処理を実行
#     form_url = create_form(tasks)  # 引数に tasks を渡す
    
#     # ユーザーにメールを送信する
#     on_send_button_click(user_id, form_url)  # form_urlを使ってメール送信

#     return jsonify({"message": "タスク情報が処理されました"}), 200