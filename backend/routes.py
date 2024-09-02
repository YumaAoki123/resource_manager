from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from email_service import create_form
from calendar_service import calculate_free_times
from auth import google, oauth
from dotenv import load_dotenv
from model.models import db, User
import secrets
import time
from authlib.integrations.requests_client import OAuth2Session
from flask import redirect, request

load_dotenv()

main = Blueprint('main', __name__)

# ホームエンドポイント
@main.route('/', methods=['GET'])
def home():
    user = session.get('user')
    if user:
        return f'Hello, {user.get("name") or user.get("email")}'
    return 'Not logged in'

@main.route('/set-session')
def set_session():
    session['key'] = 'value'
    return redirect(url_for('get_session'))

@main.route('/get-session')
def get_session():
    value = session.get('key')
    if value:
        return f'Session Value: {value}'
    return 'No session found'

# ユーザー登録
@main.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = generate_password_hash(request.form['password'], method='sha256')
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
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

# ユーザープロフィール
@main.route('/profile')
def profile():
    user = session.get('user')
    if user:
        return f"Logged in as: {user.get('email') or user.get('name')}"
    return redirect(url_for('main.login'))

# Google OAuth 2.0 ログイン
@main.route('/signup/google')
def login_google():
    # Nonce を生成してセッションに保存
    nonce = secrets.token_urlsafe(32)  # Nonceを生成
    session['nonce'] = nonce
    redirect_uri = url_for('main.auth_callback', _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce)


# Google OAuth2コールバックルート
@main.route('/auth/callback')
def auth_callback():
    token = google.authorize_access_token()
    user_info = google.parse_id_token(token, nonce=session.get('nonce'))

    user = User.query.filter_by(email=user_info['email']).first()
    if not user:
        new_user = User(email=user_info['email'], name=user_info['name'])
        db.session.add(new_user)
        db.session.commit()
        session['user'] = {'email': new_user.email, 'name': new_user.name}
    else:
        session['user'] = {'email': user.email, 'name': user.name}

    return redirect(url_for('main.home'))  # 認証成功後にリダイレクトする場所

@main.route('/api/user_info')
def api_user_info():
    if 'user' in session:
        return session['user']
    else:
        return {'error': 'Not authenticated'}, 401
                
        






# ユーザー登録 (API)
@main.route('/register', methods=['POST'])
def register():
    data = request.json
    new_user = User(username=data['name'], email=data['email'])
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201

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