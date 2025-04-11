from flask import Flask, request, redirect
from app import app as main_app

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    with main_app.test_client() as client:
        if request.method == 'POST':
            return client.post('/' + path, 
                             data=request.form,
                             headers=request.headers).get_data(as_text=True)
        return client.get('/' + path).get_data(as_text=True)
