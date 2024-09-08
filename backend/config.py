"""FlaskのConfigを提供する"""
import os

class Config:
    
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Flask
    DEBUG = True


    

    

