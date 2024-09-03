import os
from requests_oauthlib import OAuth2Session
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
client_id=os.environ.get('GOOGLE_CLIENT_ID')
client_secret=os.environ.get('GOOGLE_CLIENT_SECRET')
redirect_uri = 'http://localhost:5000/callback'

# OAuth2セッションを開始
google = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=['openid', 'email', 'profile'])

# 認証エンドポイントにリクエスト
authorization_url, state = google.authorization_url(
    'https://accounts.google.com/o/oauth2/auth',
    access_type="offline", prompt="select_account")