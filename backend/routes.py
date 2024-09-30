from flask import Blueprint,Flask, request, jsonify, session, redirect, url_for, render_template, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from email_service import create_form
from calendar_service import calculate_free_times, get_credentials, get_calendar_service
from dotenv import load_dotenv
from model.models import Base, User, db, TaskInfo, TaskConditions, EventMappings
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import uuid
from datetime import datetime, timedelta
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
import jwt
from functools import wraps


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

# トークンのデコード（検証）
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(current_user_id, *args, **kwargs)
    
    return decorated

# JWTトークンを生成する関数
def generate_jwt_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.now() + timedelta(hours=24)  # トークンの有効期限
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')
    return token

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
        db.add(new_user)
        db.commit()
        # JWTトークンを生成して返す
        token = generate_jwt_token(new_user.id)
        return jsonify({
        'message': 'User registered successfully',
        'token': token  # JWTトークンも同時に返す
    }), 201
    except IntegrityError:
        db.rollback()
        return jsonify({"error": "Username already exists"}), 409



@main.route('/auto_login', methods=['GET'])
@token_required
def auto_login(user_id):
    # ユーザーIDに基づいてユーザーを検索
    user = db.query(User).filter_by(id=user_id).first()
    
    if not user:
        return jsonify({"error": "無効なセッションIDです"}), 401

    # ユーザー情報のデバッグ出力
    print(f'user_id: {user.id}')
    print(f'username: {user.username}')

    return jsonify({"message": "Logged in", "user_id": user.id, "username": user.username}), 200

    
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
@token_required  # JWTの検証を行う
def add_task(user_id):

    print(f'user_id:{user_id}')

    data = request.get_json()
    task_name = data.get('task_name')
    
    if not task_name:
        return jsonify({"error": "Task name is required"}), 400
    print(f'data:{data}')
    task_uuid = str(uuid.uuid4())
  


    # ユーザーIDに基づいてユーザーを検索
    user = db.query(User).filter_by(id=user_id).first()
        # ユーザー情報のデバッグ出力
    print(f'user_id: {user.id}')
    print(f'username: {user.username}')
    if not user:
        return jsonify({"error": "無効なセッションIDです"}), 401

    try:
        new_task = TaskInfo(task_uuid=task_uuid, task_name=task_name, user_id=user.id)
        print(f'new_task: {new_task}')
        db.add(new_task)
        db.commit()
                # デバッグ用にデータベースから追加したタスクを再度取得
        saved_task = db.query(TaskInfo).filter_by(task_uuid=task_uuid).first()
        print(f'saved_task: id={saved_task.id}, task_uuid={saved_task.task_uuid}, task_name={saved_task.task_name}, user_id={saved_task.user_id}')

        return jsonify({"message": "Task added successfully", "task_uuid": task_uuid}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@main.route('/get_tasks_without_conditions', methods=['GET'])
@token_required  # JWTの検証を行う
def get_tasks_without_conditions(user_id):
        # デコードされたJWTのペイロードからユーザーIDを取得

    print(f'witout_condition_user_id:{user_id}')
    try:
        # セッションIDに基づいてユーザーを検索
        user = db.query(User).filter_by(id=user_id).first()
        print(f'user_id: {user.id}')
        print(f'username: {user.username}')
        if not user:
            return jsonify({"error": "無効なセッションIDです"}), 401

        # ログインしているユーザーのIDを使ってタスクを取得
        tasks = db.query(TaskInfo).outerjoin(TaskConditions, TaskInfo.task_uuid == TaskConditions.task_uuid) \
            .filter(TaskConditions.task_uuid == None, TaskInfo.user_id == user.id).all()

        # 必要なデータをリストに整形
        task_list = [{'task_uuid': task.task_uuid, 'task_name': task.task_name} for task in tasks]
        print(f'task_list: {task_list}')
        return jsonify(task_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        db.close()

@main.route('/delete_todo_task', methods=['DELETE'])
@token_required
def delete_todo_task(user_id):
    data = request.get_json()
    task_uuid = data.get('task_uuid')
    
    if not task_uuid:
        return jsonify({"error": "task_uuid is required"}), 400

    if not user_id:
        return jsonify({"error": "user_idが提供されていません"}), 400

    # ユーザー名に基づいてユーザーを検索
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "無効なセッションIDです"}), 401

    try:
        # ユーザーIDに紐づくタスクを取得
        task = db.query(TaskInfo).filter_by(task_uuid=task_uuid, user_id=user_id).first()

        if not task:
            return jsonify({"error": "Task not found or you do not have permission to delete this task"}), 404

        # 関連するtask_conditionsやevent_mappingsも削除する場合
        db.query(TaskConditions).filter_by(task_uuid=task_uuid).delete()
        db.query(EventMappings).filter_by(task_uuid=task_uuid).delete()

        # task_info自体を削除
        db.delete(task)
        db.commit()

        return jsonify({"message": "Task deleted successfully!"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@main.route("/favicon.ico")
def favicon():
    return '', 204

# クライアントからのリクエストを受け取って、指定の期間の空き時間を取得
@main.route("/get_free_times", methods=['POST'])
@token_required  # JWTの検証を行う
def get_free_times(user_id):
        print(f'freetime_user_id:{user_id}')
        data = request.get_json()
        start_date = data['start_date']
        end_date = data['end_date']
        calendar_id = data.get('calendar_id', 'primary')
        print(f'data:{data}')

            # ユーザー名に基づいてユーザーを検索
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
           return jsonify({"error": "無効なセッションIDです"}), 401
        
        # Google Calendar APIを使ってイベントを取得
        free_times = calculate_free_times(start_date, end_date, calendar_id)
        print(f'free_times_backend:{free_times}')
        return jsonify({"free_times": free_times}), 200



@main.route('/add_events_and_task_conditions', methods=['POST'])
def add_events_and_task_conditions():
    data = request.json
    task_uuid = data['task_uuid']
    task_duration = data['task_duration']
    start_date = data['start_date']
    end_date = data['end_date']
    selected_time_range = data['selected_time_range']
    selected_priority = data['selected_priority']
    min_duration = data['min_duration']
    events = data['events']

    # 1. タスク条件を保存
    save_task_conditions(task_uuid, task_duration, start_date, end_date, selected_time_range, selected_priority, min_duration)
    service = get_calendar_service()

    # 2. 各イベントをGoogle Calendarに追加
    for event_data in events:
        task_name = event_data['task_name']
        start_time = event_data['start_time']
        end_time = event_data['end_time']
        selected_priority = event_data['selected_priority']
        
                # Googleカレンダーにイベントを作成
        event = {
            'summary': task_name,
            'start': {
                'dateTime': start_time,
                'timeZone': 'Asia/Tokyo',
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Asia/Tokyo',
            },
            'colorId': str(selected_priority),
        }
        try:
            event_result = service.events().insert(calendarId='primary', body=event).execute()
            event_id = event_result.get('id')
            event_summary = event_result.get('summary')
            event_start = event_result['start'].get('dateTime', event_result['start'].get('date'))
            event_end = event_result['end'].get('dateTime', event_result['end'].get('date'))

            # イベントIDとUUIDのマッピングをデータベースに保存
            save_event_mapping(task_uuid, event_id, event_summary, event_start, event_end)

            event_results.append({
                "event_id": event_id,
                "event_summary": event_summary,
                "event_start": event_start,
                "event_end": event_end
            })
        except HttpError as error:
            return jsonify({"error": f"An error occurred: {error}"}), 500

    return jsonify({"events": event_results}), 200


def save_event_mapping(task_uuid, event_id, event_summary, event_start, event_end):

        # セッションからユーザー名とパスワードを取得
    username = session.get('username')
    print(f'username:{username}')
        # ユーザー名に基づいてユーザーを検索
    user = db.query(User).filter_by(username=username).first()
    if not user:
        return jsonify({"error": "無効なセッションIDです"}), 401
    
    try:
        new_event = EventMappings(task_uuid=task_uuid, event_id=event_id, user_id=user.id, event_summary=event_summary, event_start=event_start, event_end=event_end)
        print(f'new_event: {new_event}')
        db.add(new_event)
        db.commit()
                # デバッグ用にデータベースから追加したタスクを再度取得
        saved_event = db.query(EventMappings).filter_by(task_uuid=task_uuid).first()
        print(f'saved_task: id={saved_event.id}, task_uuid={saved_event.task_uuid}, start_time={saved_event.start_time}, user_id={saved_event.user_id}')
        return jsonify({"message": "Task added successfully", "task_uuid": task_uuid}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

def save_task_conditions(task_uuid, task_duration, start_date, end_date, selected_time_range, selected_priority, min_duration):
        # セッションからユーザー名とパスワードを取得
        # セッションからユーザー名とパスワードを取得
    username = session.get('username')
    print(f'username:{username}')
        # ユーザー名に基づいてユーザーを検索
    user = db.query(User).filter_by(username=username).first()
    if not user:
        return jsonify({"error": "無効なセッションIDです"}), 401
    
    try:
        new_event = TaskConditions(task_uuid=task_uuid, task_duration=task_duration, user_id=user.id, start_date=start_date, end_date=end_date, selected_time_range=selected_time_range, selected_priority=selected_priority, min_duration=min_duration)
        print(f'new_event: {new_event}')
        db.add(new_event)
        db.commit()
                # デバッグ用にデータベースから追加したタスクを再度取得
        saved_event = db.query(EventMappings).filter_by(task_uuid=task_uuid).first()
        print(f'saved_task: id={saved_event.id}, task_uuid={saved_event.task_uuid}, start_time={saved_event.start_time}, user_id={saved_event.user_id}')

        return jsonify({"message": "Task added successfully", "task_uuid": task_uuid}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@main.route('/login', methods=['POST'])
@token_required  # JWTの検証を行う
def login(user_id):
    print(f'login_user_id:{user_id}')
    data = request.get_json()
    username = data['username']
    password = data['password']

    
    # ユーザーをデータベースから取得
    user = db.query(User).filter_by(id=user_id).first()
    
    if user and check_password_hash(user.password, password):
        # JWTトークンを生成
        token = generate_jwt_token(user.id)
        return jsonify({'token': token}), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

# 保護されたエンドポイント
@main.route('/protected', methods=['GET'])
def protected():
    auth_header = request.headers.get('Authorization')
    if auth_header:
        token = auth_header.split(" ")[1]  # "Bearer <token>" からトークン部分を取り出す
        user_id = token_required(token)
        if user_id:
            return jsonify({'message': f'Hello, user {user_id}!'})
    return jsonify({'message': 'Unauthorized'}), 401

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