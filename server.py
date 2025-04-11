from flask import Flask, request, redirect, send_from_directory
from app import app as main_app
import os

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/<path:path>', methods=['GET', 'POST'])
def catch_all(path):
    # Handle static files
    if path.startswith('static/'):
        return send_from_directory(os.path.dirname(__file__), path)
    
    with main_app.test_client() as client:
        if request.method == 'POST':
            # Forward POST request with all data
            response = client.post(
                '/' + path,
                data=request.form,
                headers={key: value for key, value in request.headers if key != 'Host'},
                cookies=request.cookies
            )
        else:
            # Forward GET request with all data
            response = client.get(
                '/' + path,
                headers={key: value for key, value in request.headers if key != 'Host'},
                cookies=request.cookies
            )
        
        # Copy response headers
        headers = [(name, value) for name, value in response.headers if name != 'Content-Length']
        
        return response.get_data(as_text=True), response.status_code, headers
