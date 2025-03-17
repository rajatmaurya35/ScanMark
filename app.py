import os
import cv2
import qrcode
import base64
import logging
import numpy as np
import traceback
import json
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, url_for, redirect, session, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix
from logging.config import dictConfig
from pythonjsonlogger import jsonlogger
from io import BytesIO
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

def generate_qr_code():
    """Generate QR code with token and expiry"""
    token = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta(hours=24)
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    qr_data = {
        'token': token,
        'expiry': expiry.isoformat()
    }
    
    qr.add_data(json.dumps(qr_data))
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return img_io, token, expiry

def verify_token(token):
    """Verify QR token with expiry check"""
    try:
        # In production, check against database
        # For now, verify token format and basic validation
        if not token or len(token) != 43:  # URL-safe base64 token length
            return False
            
        # Check if token is expired (24 hours)
        token_data = json.loads(token)
        expiry = datetime.fromisoformat(token_data['expiry'])
        if datetime.now() > expiry:
            return False
            
        return True
    except:
        return False

@app.route('/generate-qr', methods=['GET'])
def get_qr_code():
    """Generate new QR code for attendance"""
    try:
        img_io, token, expiry = generate_qr_code()
        
        # Store QR data in memory (in production, use database)
        app.config['CURRENT_QR'] = {
            'token': token,
            'expiry': expiry
        }
        
        return send_file(
            img_io,
            mimetype='image/png',
            as_attachment=True,
            download_name='attendance_qr.png'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance with location and token verification"""
    try:
        student_id = request.form.get('student_id')
        token = request.form.get('token')
        location = request.form.get('location')
        
        # Verify QR token
        if not verify_token(token):
            return jsonify({'error': 'Invalid or expired QR code'}), 400
            
        # Basic location validation
        try:
            loc_data = json.loads(location)
            if not (-90 <= loc_data['latitude'] <= 90) or not (-180 <= loc_data['longitude'] <= 180):
                return jsonify({'error': 'Invalid location coordinates'}), 400
        except:
            return jsonify({'error': 'Invalid location data'}), 400
            
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
    registered_on = db.Column(db.DateTime, default=datetime.now)
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
