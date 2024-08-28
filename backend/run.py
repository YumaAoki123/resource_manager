from flask import Flask
from config import Config
from routes import main_routes

app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(main_routes)

if __name__ == "__main__":
    app.run(debug=True)
