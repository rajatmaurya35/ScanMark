from flask import Flask, request, send_from_directory
import os

app = Flask(__name__)

# Import all routes and configurations from app.py
from app import *

# Configure the app
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp')

# Static file handler
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# Error handler for 500 errors
@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server Error: {error}')
    return 'Internal Server Error', 500

# Error handler for 404 errors
@app.errorhandler(404)
def not_found_error(error):
    return 'Page Not Found', 404

if __name__ == '__main__':
    app.run()
