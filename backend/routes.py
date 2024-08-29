from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from models import create_connection
from email_service import create_form, on_send_button_click
import requests
from oauthlib.oauth2 import WebApplicationClient

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

discovery_url = get
# GoogleのOpenID Connectエンドポイントを取得
def get_google_provider_cfg():
    return requests.get(discovery_url).json()

# Google認証のリダイレクト先
@main_routes.route("/google_login")
def google_login():
    google_provider_cfg = get_google_provider_cfg()
    authorization_endpoint = google_provider_cfg["authorization_endpoint"]

    request_uri = client.prepare_request_uri(
        authorization_endpoint,
        redirect_uri=url_for("google_callback", _external=True),
        scope=["openid", "email", "profile", "https://www.googleapis.com/auth/calendar"],
    )
    return redirect(request_uri)

def load_tokens():
    if os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_token(user_id, token):
    tokens = load_tokens()
    tokens[user_id] = token
    with open(TOKENS_FILE, 'w') as f:
        json.dump(tokens, f)

def get_token(user_id):
    tokens = load_tokens()
    return tokens.get(user_id, None)

@app.route("/google_callback")
def google_callback():
    code = request.args.get("code")

    google_provider_cfg = get_google_provider_cfg()
    token_endpoint = google_provider_cfg["token_endpoint"]

    token_url, headers, body = client.prepare_token_request(
        token_endpoint,
        authorization_response=request.url,
        redirect_url=request.base_url,
        code=code
    )
    token_response = requests.post(
        token_url,
        headers=headers,
        data=body,
        auth=(client_id, client_secret),
    )

    client.parse_request_body_response(token_response.text)
    userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
    uri, headers, body = client.add_token(userinfo_endpoint)
    userinfo_response = requests.get(uri, headers=headers, data=body)

    if userinfo_response.json().get("email_verified"):
        session["email"] = userinfo_response.json()["email"]
        session["credentials"] = token_response.json()
        return redirect(url_for("main_app"))
    else:
        return "User email not available or not verified by Google.", 400