import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///example.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = True