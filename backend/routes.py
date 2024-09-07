from flask import Blueprint,Flask, request, jsonify, session, redirect, url_for, render_template, app
from werkzeug.security import generate_password_hash, check_password_hash
from email_service import create_form
from calendar_service import calculate_free_times
from auth import google
from dotenv import load_dotenv
from model.models import Base, User
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
from flask_session import Session
from flask import Flask, request, jsonify, session

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

load_dotenv()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
client_id = os.environ.get('GOOGLE_CLIENT_ID')
client_secret = os.environ.get('GOOGLE_CLIENT_SECRET')
redirect_uri = 'http://localhost:5000/callback'
authorization_base_url = 'https://accounts.google.com/o/oauth2/auth'
token_url = 'https://accounts.google.com/o/oauth2/token'



main = Blueprint('main', __name__)

# ホームエンドポイント
@main.route('/token_received?token={token["access_token"')
def home():

    return 'Welcome to the home page'









# ユーザー登録
@main.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    # パスワードをハッシュ化
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

    new_user = User(username=username, password=hashed_password)

    try:
        # データベースに新しいユーザーを追加
        Base.session.add(new_user)
        Base.session.commit()

        # ユーザー登録が成功したらクッキーを設定してセッションを開始
        session['username'] = username  # クッキーに保存するデータ
        return jsonify({"message": "User registered successfully!"}), 201
    except IntegrityError:
        Base.session.rollback()
        return jsonify({"error": "Username already exists"}), 409
    

@main.route('/get-free-times', methods=['POST'])
def get_free_times():
    data = request.json
    calendar_id = data.get('calendar_id', 'primary')
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    try:
        free_times = calculate_free_times(start_date, end_date, calendar_id)
        return jsonify(free_times)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    # ユーザー登録
@main.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='sha256')
        new_user = User(email=email, password=password)
        Base.session.add(new_user)
        Base.session.commit()
        return redirect(url_for('main.login'))
    return render_template('signup.html')

# ユーザーログイン
@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user'] = {'email': user.email}
            return redirect(url_for('main.profile'))
        return 'Invalid credentials'
    return render_template('login.html')


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