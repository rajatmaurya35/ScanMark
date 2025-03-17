from flask import Flask, Response
from app import app as flask_app

def init_app():
    app = Flask(__name__)
    app.wsgi_app = flask_app.wsgi_app
    return app

def handler(request):
    app = init_app()
    return Response(
        app(request.environ, lambda x, y: y),
        status=200,
        mimetype='text/html'
    )
