from flask import Flask
from config import Config
from dotenv import load_dotenv
from auth import oauth, google
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from models import db
# Load environment variables
load_dotenv()

def create_app():
    app = Flask(__name__)

    # Configure the app
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///example.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config.from_object(Config)
    
   
    
    # Initialize the database and migration
    db.init_app(app)
    migrate = Migrate(app, db)
     # Initialize OAuth
    oauth.init_app(app)
    # Register blueprints
    from routes import main  # Import blueprints here to avoid circular imports
    app.register_blueprint(main, url_prefix='/auth')
    
    # Set the secret key
    app.secret_key = os.environ.get("SECRET_KEY")

    return app