"""flask appの初期化を行い、flask appオブジェクトの実体を持つ"""
from flask import Flask
import os
from routes import main  # Import blueprints here to avoid circular imports
import model.models
from config import Config
from flask_session import Session
from datetime import timedelta
def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
    
    # セッションの設定
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')  # セッションの暗号化に必要
    Session(app)
    app.config['SESSION_COOKIE_NAME'] = 'session'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(weeks=2)  # セッションの有効期限を1週間に設定
    # Register blueprints
    app.register_blueprint(main)

    return app

app = create_app()