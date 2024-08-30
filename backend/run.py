from flask import Flask
from config import Config
from routes import main
from dotenv import load_dotenv
from auth import oauth, google
import os

load_dotenv()

app = Flask(__name__)

app.config.from_object(Config)

app.config['SESSION_COOKIE_SECURE'] = True  # セキュリティ強化オプション
app.register_blueprint(main)
app.secret_key = os.environ.get("SECRET_KEY")

oauth.init_app(app)



if __name__ == "__main__":
    app.run(debug=True)
