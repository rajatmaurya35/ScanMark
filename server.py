from flask import Flask, request, redirect
from app import app as main_app

app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    with main_app.test_client() as client:
        return client.get('/' + path).get_data(as_text=True)
