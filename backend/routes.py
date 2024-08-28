from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from models import create_connection
from email_service import create_form, on_send_button_click

main_routes = Blueprint('main', __name__)

# ホームエンドポイント
@main_routes.route('/', methods=['GET'])
def home():
    return "Welcome to the Home Page!", 200

@main_routes.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "メールアドレスとパスワードが必要です"}), 400
    
    conn = create_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()

    if user and check_password_hash(user[2], password):  # user[2] はパスワードハッシュ
        # セッションの管理など
        return jsonify({"message": "ログイン成功"}), 200
    else:
        return jsonify({"error": "無効なメールアドレスまたはパスワード"}), 401
    

@main_routes.route('/logout', methods=['POST'])
def logout():
    # セッションの管理など
    return jsonify({"message": "ログアウト成功"}), 200



@main_routes.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"error": "メールアドレスとパスワードは必須です"}), 400

    # パスワードをハッシュ化
    hashed_password = generate_password_hash(password)

    # データベースに保存する処理
    conn = create_connection()
    cursor = conn.cursor()

    # 既存のユーザーをチェック
    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    if cursor.fetchone():
        return jsonify({"error": "このメールアドレスは既に登録されています"}), 400

    cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, hashed_password))
    conn.commit()

    # ユーザーIDの取得
    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
    user_id = cursor.fetchone()[0]
    conn.close()

    # セッションにユーザー情報を保存（自動ログイン）
    session['user_id'] = user_id
    session['email'] = email

    return jsonify({"message": "ユーザー登録が完了し、ログインしました"}), 200


# # メールアドレス登録エンドポイント
# @main_routes.route('/register', methods=['POST'])
# def register_email():
#     email = request.form.get('email')
    
#     if not email:
#         return jsonify({"error": "メールアドレスが必要です"}), 400
    
#     conn = create_connection()
#     try:
#         with conn:
#             conn.execute('INSERT INTO users (email) VALUES (?)', (email,))
#                # ログに出力して確認
#             print(f"Email received and saved: {email}")
#         return jsonify({"message": "メールアドレスが登録されました"}), 200
     
#     except sqlite3.IntegrityError:
#         return jsonify({"error": "このメールアドレスは既に登録されています"}), 400
#     finally:
#         conn.close()

@main_routes.route('/submit-tasks', methods=['POST'])
def submit_tasks():
    data = request.get_json()
    
    user_id = data.get('user_id')
    tasks = data.get('tasks')

    if not user_id or not tasks:
        return jsonify({"error": "ユーザIDとタスク情報が必要です"}), 400
    
    # ここでタスク情報をフォームに追加するために必要な処理を実行
    form_url = create_form(tasks)  # 引数に tasks を渡す
    
    # ユーザーにメールを送信する
    on_send_button_click(user_id, form_url)  # form_urlを使ってメール送信

    return jsonify({"message": "タスク情報が処理されました"}), 200