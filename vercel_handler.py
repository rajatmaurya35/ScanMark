from flask import Flask
from app import app as flask_app

def init_app():
    app = Flask(__name__)
    app.config.update(flask_app.config)
    app.register_blueprint(flask_app)
    return app

app = init_app()

# Vercel handler
def handler(event, context):
    return app(event, context)
