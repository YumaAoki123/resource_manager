from flask import Blueprint,Flask, request, jsonify, session, redirect, url_for, render_template, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from calendar_service import calculate_free_times, get_credentials
from dotenv import load_dotenv
from model.models import Base, User, db, TaskInfo, TaskConditions, EventMappings,Token
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
from google.oauth2.credentials import Credentials
import json
from dateutil import parser
import urllib.parse
# クライアントIDとクライアントシークレットを環境変数から取得する
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # HTTPSを強制しないようにする（ローカル開発用）

# 環境変数からクライアントIDとリダイレクトURIを取得
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
REDIRECT_URI = os.getenv("REDIRECT_URIS")
SCOPE = "openid email profile"

# 認可のためのスコープ
scope = ["https://www.googleapis.com/auth/calendar"]

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
@token_required
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
    
    # ユーザーIDに基づいてユーザーを検索
    user = db.query(User).filter_by(id=user_id).first()
    
    # ユーザー情報のデバッグ出力
    if not user:
        return jsonify({"error": "無効なセッションIDです"}), 401

    print(f'user_id: {user.id}')
    print(f'username: {user.username}')
    
    try:
        # 新しいタスクをTaskInfoテーブルに追加
        new_task = TaskInfo(task_name=task_name, user_id=user.id)
        print(f'new_task: {new_task}')
        db.add(new_task)
        db.commit()
        
        # デバッグ用にデータベースから追加したタスクを再度取得
        saved_task = db.query(TaskInfo).filter_by(id=new_task.id).first()
        print(f'saved_task: id={saved_task.id}, task_name={saved_task.task_name}, user_id={saved_task.user_id}')

        # 返却するレスポンスでtask_uuidではなくidを返す
        return jsonify({"message": "Task added successfully", "task_id": saved_task.id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@main.route('/get_tasks_without_conditions', methods=['GET'])
@token_required  # JWTの検証を行う
def get_tasks_without_conditions(user_id):
    print(f'without_condition_user_id: {user_id}')
    try:
        # セッションIDに基づいてユーザーを検索
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "無効なセッションIDです"}), 401

        print(f'user_id: {user.id}')
        print(f'username: {user.username}')

        # TaskInfo に関連する TaskConditions が存在しないタスクを取得
        tasks = (
            db.query(TaskInfo, TaskConditions)
            .outerjoin(TaskConditions, TaskInfo.id == TaskConditions.task_id)
            .filter(TaskConditions.task_id == None, TaskInfo.user_id == user.id)
            .all()
        )

        # 各タスクに関連するデータをリストに追加
        task_list = []
        for task_info, task_conditions in tasks:
            task_data = {
                'task_id': task_info.id,
                'task_name': task_info.task_name,
            }

            # TaskConditions のデータが存在する場合、task_duration を取得してデバッグ出力
            if task_conditions:
                print(f"task_conditions.task_duration: {task_conditions.task_duration}")
                task_data['task_duration'] = task_conditions.task_duration
            else:
                task_data['task_duration'] = None  # TaskConditions が存在しない場合は None にする

            task_list.append(task_data)

        print(f'task_list: {task_list}')
        return jsonify(task_list), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        db.close()


@main.route('/get_schedules', methods=['GET'])
@token_required  # JWTの検証を行う
def get_schedules(user_id):
    print(f'get_schedules_user_id: {user_id}')
    try:
        # ユーザーの確認
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "無効なセッションIDです"}), 401

        print(f'username: {user.username}')

        # task_info と task_conditions を結合し、task_conditions に task_id が存在するものを取得
        schedules = (
            db.query(TaskInfo.task_name, TaskConditions.task_id, TaskConditions.task_duration, 
                     TaskConditions.start_date, TaskConditions.end_date, TaskConditions.selected_time_range,
                     TaskConditions.selected_priority, TaskConditions.min_duration)
            .join(TaskConditions, TaskInfo.id == TaskConditions.task_id)
            .filter(TaskInfo.user_id == user.id)  # ユーザーIDでフィルタリング
            .all()
        )

        # データをリストに追加
        schedule_list = []
        for schedule in schedules:
            task_data = {
                'task_name': schedule[0],  # TaskInfo.task_name
                'task_id': schedule[1],  # TaskConditions.task_id
                'task_duration': schedule[2],  # TaskConditions.task_duration
                'start_date': schedule[3],  # TaskConditions.start_date
                'end_date': schedule[4],  # TaskConditions.end_date
                'selected_time_range': schedule[5],  # TaskConditions.selected_priority
                'selected_priority': schedule[6],  # TaskConditions.selected_priority
                'min_duration': schedule[7]  # TaskConditions.min_duration
            }
            schedule_list.append(task_data)

        print(f'schedule_list: {schedule_list}')
        return jsonify(schedule_list), 200

    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"error": str(e)}), 500

    finally:
        db.close()


@main.route('/delete_todo_task', methods=['DELETE'])
@token_required
def delete_todo_task(user_id):
    data = request.get_json()
    task_id = data.get('task_id')
    
    if not task_id:
        return jsonify({"error": "task_id is required"}), 400

    if not user_id:
        return jsonify({"error": "user_idが提供されていません"}), 400

    # ユーザー名に基づいてユーザーを検索
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "無効なセッションIDです"}), 401

    try:
        # ユーザーIDに紐づくタスクを取得
        task = db.query(TaskInfo).filter_by(task_id=task_id, user_id=user_id).first()

        if not task:
            return jsonify({"error": "Task not found or you do not have permission to delete this task"}), 404

        # 関連するtask_conditionsやevent_mappingsも削除する場合
        db.query(TaskConditions).filter_by(task_id=task_id).delete()
        db.query(EventMappings).filter_by(task_id=task_id).delete()

        # task_info自体を削除
        db.delete(task)
        db.commit()

        return jsonify({"message": "Task deleted successfully!"}), 200
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@main.route('/get_event_mappings', methods=['POST'])
@token_required  # JWTの検証を行う
def get_event_mappings(user_id):
    data = request.get_json()
    task_id = data.get('task_id')
    print(f'task_id: {task_id}')
    print(f'get_event_mappings_id: {user_id}')

    # 現在の時間を取得（Asia/Tokyo タイムゾーンに設定）
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    current_time = datetime.now(tokyo_tz)
    print(f"current_time_fetch{current_time}")

    try:
        # ユーザーの確認
        user = db.query(User).filter_by(id=user_id).first()
        if not user:
            return jsonify({"error": "無効なセッションIDです"}), 401

        print(f'username: {user.username}')

        # EventMappingsテーブルから現在の時刻より前のstart_timeとend_timeを取得
        events = (
            db.query(EventMappings.start_time, EventMappings.end_time)
            .filter(EventMappings.user_id == user_id)  # ユーザーIDでフィルタリング
            .filter(EventMappings.task_id == task_id)  # task_idでフィルタリング
            .filter(EventMappings.end_time < current_time)  # start_timeが現在時刻より前のもの
            .all()
        )

        # データをリストに追加
        event_list = []
        for event in events:
            event_data = {
                'start_time': event[0],  # TaskInfo.task_name
                'end_time': event[1],  # TaskConditions.task_id
            }
            event_list.append(event_data)

        print(f'schedule_list: {event_list}')
        return jsonify(event_list), 200

    except Exception as e:
        print(f"Error: {str(e)}")
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
        free_times = calculate_free_times(start_date, end_date, user_id, calendar_id)
        print(f'free_times_backend:{free_times}')
        return jsonify({"free_times": free_times}), 200



@main.route('/add_events_and_task_conditions', methods=['POST'])
@token_required
def add_events_and_task_conditions(user_id):
    print(f'add_events_user_id:{user_id}')
    data = request.json
    task_id = data['task_id']  # task_uuidの代わりにtask_idを使用
    task_duration = data['task_duration']
    start_date = data['start_date']
    end_date = data['end_date']
    selected_time_range = data['selected_time_range']
    selected_priority = data['selected_priority']
    min_duration = data['min_duration']
    events = data['events']

    # 1. タスク条件を保存
    save_task_conditions(task_id, task_duration, start_date, end_date, selected_time_range, selected_priority, min_duration, user_id)
    credentials = get_credentials(user_id)

    # Google Calendar APIのサービスオブジェクトを作成
    service = build('calendar', 'v3', credentials=credentials)

    event_results = []  # イベント結果の初期化

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

            # イベントIDとタスクIDのマッピングをデータベースに保存
            save_event_mapping(task_id, event_id, event_summary, event_start, event_end, user_id)

            event_results.append({
                "event_id": event_id,
                "event_summary": event_summary,
                "event_start": event_start,
                "event_end": event_end
            })
        except HttpError as error:
            return jsonify({"error": f"An error occurred: {error}"}), 500

    return jsonify({"events": event_results}), 200


def save_event_mapping(task_id, event_id, event_summary, event_start, event_end, user_id):
    print(f'save_mappings_user_id:{user_id}')
    
    # ユーザーを検索
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "無効なセッションIDです"}), 401
    parsed_event_start = parser.parse(event_start)
    parsed_event_end = parser.parse(event_end)

    try:
        new_event = EventMappings(task_id=task_id, event_id=event_id, summary=event_summary, start_time=parsed_event_start, end_time=parsed_event_end, user_id=user_id)
        print(f'new_event: {new_event}')
        db.add(new_event)
        db.commit()
        
        # デバッグ用にデータベースから追加したイベントを再度取得
        saved_event = db.query(EventMappings).filter_by(task_id=task_id).first()
        print(f'saved_task: id={saved_event.id}, task_id={saved_event.task_id}, start_time={saved_event.start_time}, user_id={saved_event.user_id}')
        
        return jsonify({"message": "Event added successfully", "task_id": task_id}), 201
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

def save_task_conditions(task_id, task_duration, start_date, end_date, selected_time_range, selected_priority, min_duration, user_id):
    print(f'save_condition_user_id:{user_id}')
    
    # ユーザーを検索
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return jsonify({"error": "無効なセッションIDです"}), 401
    parsed_start = parser.parse(start_date)
    parsed_end = parser.parse(end_date)

    try:
        new_condition = TaskConditions(task_id=task_id, task_duration=task_duration, user_id=user.id, start_date=parsed_start, end_date=parsed_end, selected_time_range=selected_time_range, selected_priority=selected_priority, min_duration=min_duration)
                # 作成したタスク条件をデバッグ出力
        print(f'new_condition: {new_condition}')
        print(f'task_id: {task_id}, task_duration: {task_duration}, user_id: {user_id}')

        db.add(new_condition)
        db.commit()

        # デバッグ用にデータベースから追加したタスク条件を再取得
        saved_conditions = db.query(TaskConditions).filter_by(task_id=task_id).first()
        # 再取得したデータをデバッグ出力
        if saved_conditions:
            print(f'saved_conditions: id={saved_conditions.id}, task_id={saved_conditions.task_id}, task_duration={saved_conditions.task_duration}, selected_priority={saved_conditions.selected_priority}')
        else:
            print("Task condition was not saved correctly.")
        
        return jsonify({"message": "Task conditions added successfully", "task_id": task_id}), 201
    except Exception as e:
        db.rollback()
        print(f"Error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()


@main.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data['username']
    password = data['password']

    
    # ユーザーをデータベースから取得
    user = db.query(User).filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):
        # JWTトークンを生成
        token = generate_jwt_token(user.id)
        return jsonify({'token': token}), 200
    else:
        return jsonify({'message': 'Invalid credentials'}), 401

@main.route('/registar_email', methods=['POST'])
@token_required
def registar_email(user_id):
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({"error": "Email is required"}), 400

    print(f'email: {email}')

    # user_id に基づいてユーザーを検索
    user = db.query(User).filter_by(id=user_id).first()
    
    if not user:
        return jsonify({"error": "Invalid user ID"}), 401
    
    try:
        # メールアドレスをユーザーに保存
        user.email = email
        db.commit()

        return jsonify({
            'message': 'Email registered successfully',
        }), 200

    except IntegrityError:
        db.rollback()
        return jsonify({"error": "Email already exists"}), 409

    finally:
        db.close()

    
@main.route('/auth_url', methods=['POST'])
def get_auth_url():
    state = "some_unique_state"  # CSRF対策のためのstate
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}&"
        f"scope={urllib.parse.quote(SCOPE)}&"
        f"state={state}"
    )
    return jsonify({"auth_url": auth_url})

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