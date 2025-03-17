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

def generate_qr_code(data, filename):
    """Generate QR code with error handling"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(os.path.join('static', 'qr_codes', filename))
        return True
    except Exception as e:
        app.logger.error(f"Error generating QR code: {str(e)}")
        return False

def validate_biometric_data(face_data, fingerprint_data):
    """Validate biometric data for security"""
    try:
        if not face_data or not fingerprint_data:
            return False, "Missing biometric data"
            
        # Validate face data format (base64 encoded image)
        try:
            face_bytes = base64.b64decode(face_data.split(',')[1])
            face_array = np.frombuffer(face_bytes, dtype=np.uint8)
            face_img = cv2.imdecode(face_array, cv2.IMREAD_COLOR)
            if face_img is None:
                return False, "Invalid face image format"
        except:
            return False, "Invalid face data"
            
        # Validate fingerprint data format
        try:
            fingerprint_bytes = base64.b64decode(fingerprint_data)
            if len(fingerprint_bytes) < 100:  # Minimum size check
                return False, "Invalid fingerprint data size"
        except:
            return False, "Invalid fingerprint data"
            
        return True, ""
    except Exception as e:
        app.logger.error(f"Error validating biometric data: {str(e)}")
        return False, "Error processing biometric data"

def validate_location(latitude, longitude, ip_address):
    """Basic location validation"""
    try:
        # Just validate coordinate ranges
        if not (-90 <= float(latitude) <= 90) or not (-180 <= float(longitude) <= 180):
            return False, "Invalid coordinates"
        return True, ""
    except Exception as e:
        app.logger.error(f"Error validating location: {str(e)}")
        return False, "Error validating location"

def validate_network_security(request):
    """Validate network security based on environment"""
    try:
        if env == 'production':
            # Stricter validation in production
            if not request.is_secure:
                return False, "Connection is not secure (HTTPS required)"
                
            headers = request.headers
            origin = headers.get('Origin', '')
            if origin and not origin.startswith('https://'):
                return False, "Invalid origin"
        
        # Basic validation for all environments
        user_agent = request.headers.get('User-Agent', '')
        if not user_agent or len(user_agent) < 5:
            return False, "Invalid user agent"
            
        return True, ""
    except Exception as e:
        app.logger.error(f"Error validating network security: {str(e)}")
        return False, "Error validating network security"

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

@app.route('/mark-attendance/<token>')
@limiter.limit("5 per minute")
def mark_attendance_form(token):
    try:
        daily_qr = DailyQR.query.filter_by(token=token).first()
        if not daily_qr or daily_qr.expiry < CURRENT_TIME:
            return "Invalid or expired QR code", 400
            
        if daily_qr.used_count >= 100:  # Limit token usage
            return "QR code has been used too many times", 400
        
        return render_template('mark_attendance.html', token=token)
    except Exception as e:
        app.logger.error(f"Error in mark_attendance_form: {str(e)}")
        return "An error occurred", 500

@app.route('/api/mark-attendance', methods=['POST'])
@limiter.limit("3 per minute")
def mark_attendance():
    try:
        data = request.json
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data received'
            }), 400
            
        # Validate required fields
        required_fields = ['token', 'roll_number', 'name', 'course', 'year', 'division']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
            
        # Validate student data format and security
        is_valid, error_message = validate_student_data(data)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': error_message
            }), 400
            
        # Validate biometric data
        face_data = data.get('face_data', '')
        fingerprint_data = data.get('fingerprint_data', '')
        is_valid, error_message = validate_biometric_data(face_data, fingerprint_data)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': error_message
            }), 400
            
        # Validate location data
        try:
            latitude = float(data.get('latitude', 0))
            longitude = float(data.get('longitude', 0))
            is_valid, error_message = validate_location(latitude, longitude, request.remote_addr)
            if not is_valid:
                return jsonify({
                    'success': False,
                    'message': error_message
                }), 400
        except (TypeError, ValueError):
            return jsonify({
                'success': False,
                'message': 'Invalid location coordinates'
            }), 400
            
        # Validate network security
        is_valid, error_message = validate_network_security(request)
        if not is_valid:
            return jsonify({
                'success': False,
                'message': error_message
            }), 400
            
        token = data.get('token')
        
        # Verify token
        daily_qr = DailyQR.query.filter_by(token=token).first()
        if not daily_qr:
            return jsonify({
                'success': False,
                'message': 'Invalid QR code'
            }), 400
            
        if daily_qr.expiry < CURRENT_TIME:
            return jsonify({
                'success': False,
                'message': 'QR code has expired'
            }), 400
            
        if daily_qr.used_count >= 100:
            return jsonify({
                'success': False,
                'message': 'QR code has been used too many times'
            }), 400
        
        # Get or create student
        student = Student.query.filter_by(roll_number=data['roll_number']).first()
        if not student:
            student = Student(
                roll_number=data['roll_number'],
                name=data['name'],
                course=data['course'],
                year=data['year'],
                division=data['division'],
                face_data=base64.b64decode(face_data.split(',')[1]) if face_data else None,
                fingerprint_data=base64.b64decode(fingerprint_data) if fingerprint_data else None
            )
            db.session.add(student)
            db.session.commit()
        
        # Check if attendance already marked
        today = CURRENT_TIME.date()
        existing_attendance = Attendance.query.filter_by(
            student_id=student.id,
            date=today
        ).first()
        
        if existing_attendance:
            return jsonify({
                'success': False,
                'message': 'Attendance already marked for today'
            }), 400
        
        # Mark attendance with additional security info
        attendance = Attendance(
            student_id=student.id,
            date=CURRENT_TIME.date(),
            time=CURRENT_TIME.time(),
            latitude=latitude,
            longitude=longitude,
            status='late' if CURRENT_TIME.hour >= 9 and CURRENT_TIME.minute > 15 else 'present',
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', ''),
            face_verified=True,
            fingerprint_verified=True
        )
        
        # Increment token usage
        daily_qr.used_count += 1
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Attendance marked successfully',
            'redirect_url': url_for('student_dashboard', roll_number=student.roll_number)
        })
    except Exception as e:
        app.logger.error(f"Error marking attendance: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while marking attendance'
        }), 500

@app.route('/student-dashboard/<roll_number>')
@limiter.limit("20 per minute")
def student_dashboard(roll_number):
    try:
        student = Student.query.filter_by(roll_number=roll_number).first_or_404()
        
        # Get attendance records
        attendance_records = Attendance.query.filter_by(student_id=student.id).order_by(Attendance.date.desc()).all()
        
        # Calculate stats
        total_days = len(attendance_records)
        present_days = len([a for a in attendance_records if a.status == 'present'])
        late_days = len([a for a in attendance_records if a.status == 'late'])
        
        attendance_percentage = (present_days / total_days * 100) if total_days > 0 else 0
        
        return render_template('student_dashboard.html',
                             student=student,
                             attendance_records=attendance_records,
                             stats={
                                 'total': total_days,
                                 'present': present_days,
                                 'late': late_days,
                                 'percentage': round(attendance_percentage, 2)
                             })
    except Exception as e:
        app.logger.error(f"Error in student_dashboard: {str(e)}")
        return "An error occurred", 500

def validate_student_data(data):
    """Validate student data for security and data integrity"""
    # Validate roll number format (e.g., CS2025XXX)
    if not data.get('roll_number') or not re.match(r'^CS\d{7}$', data.get('roll_number')):
        return False, 'Invalid roll number format. Must be CS followed by 7 digits'
        
    # Validate name (only letters, spaces, and common punctuation)
    if not data.get('name') or not re.match(r'^[A-Za-z\s\'-]{2,100}$', data.get('name')):
        return False, 'Invalid name format'
        
    # Validate course (only letters, spaces, and common punctuation)
    if not data.get('course') or not re.match(r'^[A-Za-z\s\'-]{2,100}$', data.get('course')):
        return False, 'Invalid course format'
        
    # Validate year (First Year to Fifth Year only)
    valid_years = ['First Year', 'Second Year', 'Third Year', 'Fourth Year', 'Fifth Year']
    if not data.get('year') or data.get('year') not in valid_years:
        return False, 'Invalid year. Must be between First Year and Fifth Year'
        
    # Validate division (single uppercase letter)
    if not data.get('division') or not re.match(r'^[A-Z]$', data.get('division')):
        return False, 'Invalid division format. Must be a single uppercase letter'
        
    return True, ''

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
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    status = db.Column(db.String(20), default='present')
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))
    face_verified = db.Column(db.Boolean, default=False)  # Track face verification
    fingerprint_verified = db.Column(db.Boolean, default=False)  # Track fingerprint verification

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
