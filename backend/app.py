"""flask appの初期化を行い、flask appオブジェクトの実体を持つ"""
from flask import Flask
import os
from routes import main  # Import blueprints here to avoid circular imports
import model.models
from config import Config
from flask_session import Session

def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)
     # Set the secret key
    app.secret_key = os.environ.get('SECRET_KEY')
    
    # セッションの設定
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SECRET_KEY'] = 'supersecretkey'  # セッションの暗号化に必要
    Session(app)
    
    # Register blueprints
    app.register_blueprint(main)

    return app

app = create_app()