from flask import Blueprint,Flask, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from email_service import create_form
from calendar_service import calculate_free_times
from dotenv import load_dotenv
from model.models import Base, User, db_session
import secrets
import time
from flask import redirect, request
import os
import requests
import webbrowser
from requests_oauthlib import OAuth2Session
from flask_session import Session
import json
from flask import Flask, request, jsonify, session
import sqlite3
import bcrypt
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

load_dotenv()


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


# @main.route('/get-free-times', methods=['POST'])
# def get_free_times():
#     data = request.json
#     calendar_id = data.get('calendar_id', 'primary')
#     start_date = data.get('start_date')
#     end_date = data.get('end_date')

#     try:
#         free_times = calculate_free_times(start_date, end_date, calendar_id)
#         return jsonify(free_times)
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500



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