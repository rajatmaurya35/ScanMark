from flask import Flask, request, send_from_directory, jsonify
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

app = Flask(__name__)
logger = app.logger

# Import all routes and configurations from app.py
try:
    from app import *
    logger.info('Successfully imported routes from app.py')
except Exception as e:
    logger.error(f'Error importing app.py: {str(e)}')
    raise

# Configure the app
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp')

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Static file handler
@app.route('/static/<path:filename>')
def serve_static(filename):
    try:
        return send_from_directory('static', filename)
    except Exception as e:
        logger.error(f'Error serving static file {filename}: {str(e)}')
        return 'File not found', 404

# Error handler for 500 errors
@app.errorhandler(500)
def internal_error(error):
    logger.error(f'Server Error: {error}')
    if app.debug:
        return jsonify({
            'error': 'Internal Server Error',
            'message': str(error),
            'type': error.__class__.__name__
        }), 500
    return jsonify({'error': 'Internal Server Error'}), 500

# Error handler for 404 errors
@app.errorhandler(404)
def not_found_error(error):
    logger.warning(f'Page not found: {request.url}')
    return jsonify({'error': 'Page Not Found'}), 404

if __name__ == '__main__':
    app.run()
