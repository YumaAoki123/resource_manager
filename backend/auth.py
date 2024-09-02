from authlib.integrations.flask_client import OAuth
import os
oauth = OAuth()

# Google OAuthの設定
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    redirect_uri='http://localhost:5000/auth/callback',
    scope='openid profile email',
)

