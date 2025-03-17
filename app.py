import os
import cv2
import qrcode
import base64
import logging
import numpy as np
import traceback
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, url_for, redirect, session
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix
from logging.config import dictConfig
from pythonjsonlogger import jsonlogger
from config import config

# Configure logging
dictConfig({
    'version': 1,
    'formatters': {
        'json': {
            '()': jsonlogger.JsonFormatter,
            'format': '%(timestamp)s %(level)s %(name)s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
            'stream': 'ext://sys.stdout'
        }
    },
    'root': {
        'level': os.getenv('LOG_LEVEL', 'INFO'),
        'handlers': ['console']
    }
})

# Initialize Flask app
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Load configuration
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Current time for testing (2025-03-17 09:30:25+05:30)
CURRENT_TIME = datetime(2025, 3, 17, 9, 30, 25)

# Initialize security extensions
Talisman(app, 
    force_https=True if env == 'production' else False,
    strict_transport_security=True if env == 'production' else False,
    session_cookie_secure=True if env == 'production' else False,
    content_security_policy={
        'default-src': ["'self'", "*" if env == 'development' else "https:", "data:", "blob:"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "*" if env == 'development' else "https:"],
        'style-src': ["'self'", "'unsafe-inline'", "*" if env == 'development' else "https:"],
        'img-src': ["'self'", "data:", "*" if env == 'development' else "https:", "blob:"],
        'font-src': ["'self'", "*" if env == 'development' else "https:"],
        'media-src': ["'self'", "blob:", "*" if env == 'development' else "https:"],
        'worker-src': ["'self'", "blob:", "*" if env == 'development' else "https:"],
        'connect-src': ["'self'", "*" if env == 'development' else "https:"]
    },
    content_security_policy_nonce_in=['script-src'],
    force_file_save=True,
    x_content_type_options=True,
    frame_options='SAMEORIGIN',
    referrer_policy='no-referrer'
)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=app.config['RATELIMIT_DEFAULT'],
    storage_uri=app.config['RATELIMIT_STORAGE_URL']
)

# Initialize database
db = SQLAlchemy(app)

# Create static directory
os.makedirs(os.path.join('static', 'qr_codes'), exist_ok=True)

def get_public_url():
    """Get the public URL for QR code generation"""
    if env == 'production':
        return os.getenv('PUBLIC_URL', 'https://your-domain.com')
    else:
        return request.host_url.rstrip('/')

def verify_biometric(image_data):
    """Verify biometric data using cloud service"""
    try:
        # For development, return success
        # In production, integrate with a cloud biometric service
        return True, "Verification successful"
    except Exception as e:
        return False, str(e)

def verify_token(token):
    """Verify QR token"""
    try:
        # For development, return success
        # In production, integrate with a token verification service
        return True
    except Exception as e:
        return False

def verify_location(location):
    """Verify location"""
    try:
        # For development, return success
        # In production, integrate with a location verification service
        return True
    except Exception as e:
        return False

@app.route('/')
def index():
    try:
        # Generate new QR code
        token = os.urandom(16).hex()
        expiry = CURRENT_TIME + app.config['QR_CODE_EXPIRY']
        
        daily_qr = DailyQR(
            token=token,
            expiry=expiry,
            used_count=0
        )
        db.session.add(daily_qr)
        db.session.commit()
        
        # Generate QR code with public URL
        public_url = get_public_url()
        qr_url = f"{public_url}/mark-attendance?token={token}"
        filename = f"qr_{token}.png"
        
        if not generate_qr_code(qr_url, filename):
            return "Error generating QR code", 500
        
        return render_template('index.html', 
                             qr_code=url_for('static', filename=f'qr_codes/{filename}'),
                             token=token,
                             expiry=expiry)
    except Exception as e:
        app.logger.error(f"Error in index route: {str(e)}")
        return "An error occurred", 500

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    try:
        # Get form data
        student_id = request.form.get('student_id')
        token = request.form.get('token')
        location = request.form.get('location')
        
        # Verify QR token
        if not verify_token(token):
            return jsonify({'error': 'Invalid or expired QR code'}), 400
            
        # Verify location
        if not verify_location(location):
            return jsonify({'error': 'Invalid location'}), 400
            
        # Record attendance
        attendance = Attendance(
            student_id=student_id,
            date=datetime.now(),
            status='present',
            location=location
        )
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Attendance marked successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    course = db.Column(db.String(100))
    year = db.Column(db.String(20))
    division = db.Column(db.String(10))
    registered_on = db.Column(db.DateTime, default=CURRENT_TIME)
    face_data = db.Column(db.LargeBinary, nullable=True)  # Store face recognition data
    fingerprint_data = db.Column(db.LargeBinary, nullable=True)  # Store fingerprint data
    attendances = db.relationship('Attendance', backref='student', lazy=True)

    def __repr__(self):
        return f'<Student {self.roll_number}>'

class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='present')
    location = db.Column(db.String(100))

    def __repr__(self):
        return f'<Attendance {self.student_id} {self.date}>'

class DailyQR(db.Model):
    __tablename__ = 'daily_qrs'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)
    used_count = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f'<DailyQR {self.token}>'

if __name__ == '__main__':
    # Initialize database
    with app.app_context():
        db.create_all()
    
    print("\nServer Information:")
    print("-" * 50)
    server_ip = get_public_url()
    print(f"Server IP: {server_ip}")
    print(f"Server URL: https://{server_ip}:5000")
    print("-" * 50)
    print("\nStarting server with SSL...")
    
    # Enable debug mode and run with SSL
    app.debug = True
    app.run(
        host='0.0.0.0',  # Listen on all interfaces for testing
        port=5000,
        ssl_context='adhoc'  # Use Flask's built-in development SSL
    )
