"""flask appの初期化を行い、flask appオブジェクトの実体を持つ"""
from flask import Flask
from database import init_db
import os
from auth import oauth
from routes import main  # Import blueprints here to avoid circular imports
import model.models

def create_app():
    app = Flask(__name__)

    app.config.from_object('config.Config')
     # Set the secret key
    app.secret_key = os.environ.get("SECRET_KEY")
   
    
    # Initialize the database and migration
    init_db(app)
     # Initialize OAuth
    oauth.init_app(app)
    
    # Register blueprints
    app.register_blueprint(main, url_prefix='/auth')

    return app

app = create_app()