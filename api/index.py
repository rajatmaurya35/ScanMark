from flask import Flask, jsonify, request, send_file, render_template
import os
import json
import secrets
import base64
import numpy as np
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from io import BytesIO
import qrcode
from PIL import Image

app = Flask(__name__)

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_iaL8ckJzYN7X@ep-shy-smoke-a5mn2t1d-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'ufsOrYXqhAM2Uo5TOdfWE6SHRWRrNCcliNEMv4MXApI')

# Initialize database
db = SQLAlchemy(app)

# Enable CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

# Database Models
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    face_template = db.Column(db.LargeBinary)
    fingerprint_template = db.Column(db.LargeBinary)
    registered_on = db.Column(db.DateTime, default=datetime.now)

class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='present')
    location = db.Column(db.String(100))
    verification_method = db.Column(db.String(20))

class QRToken(db.Model):
    __tablename__ = 'qr_tokens'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

def process_image_template(image_data):
    """Process base64 image and return simplified template"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(image_data.split(',')[1])
        image = Image.open(BytesIO(image_data))
        
        # Convert to grayscale and resize
        image = image.convert('L').resize((64, 64))
        
        # Convert to numpy array and normalize
        array = np.array(image)
        array = array.astype(np.float32) / 255.0
        
        return array.tobytes()
    except Exception as e:
        return None

def compare_templates(template1, template2, threshold=0.7):
    """Compare two templates using simple correlation"""
    try:
        # Convert to numpy arrays
        array1 = np.frombuffer(template1, dtype=np.float32).reshape(64, 64)
        array2 = np.frombuffer(template2, dtype=np.float32).reshape(64, 64)
        
        # Calculate correlation
        correlation = np.corrcoef(array1.flatten(), array2.flatten())[0, 1]
        return correlation > threshold
    except Exception as e:
        return False

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        db.session.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/generate-qr')
def generate_qr():
    """Generate QR code for attendance"""
    try:
        # Generate token and expiry
        token = secrets.token_urlsafe(16)
        expiry = datetime.now() + timedelta(minutes=5)
        
        # Save token
        qr_token = QRToken(token=token, expiry=expiry)
        db.session.add(qr_token)
        db.session.commit()
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps({'token': token, 'expiry': expiry.isoformat()}))
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['POST'])
def register():
    """Register new student with biometric data"""
    try:
        data = request.form
        student_id = data.get('student_id')
        name = data.get('name')
        face_data = data.get('face_template')
        fingerprint_data = data.get('fingerprint_template')
        
        if not all([student_id, name, face_data, fingerprint_data]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Process templates
        face_template = process_image_template(face_data)
        finger_template = process_image_template(fingerprint_data)
        
        if not face_template or not finger_template:
            return jsonify({'error': 'Failed to process biometric data'}), 400
        
        # Create student
        student = Student(
            student_id=student_id,
            name=name,
            face_template=face_template,
            fingerprint_template=finger_template
        )
        
        db.session.add(student)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration successful'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance with biometric verification"""
    try:
        data = request.form
        student_id = data.get('student_id')
        token = data.get('token')
        location = data.get('location')
        face_data = data.get('face_template')
        fingerprint_data = data.get('fingerprint_template')
        
        if not all([student_id, token, location, face_data, fingerprint_data]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Verify token
        qr_token = QRToken.query.filter_by(token=token).first()
        if not qr_token or qr_token.expiry < datetime.now():
            return jsonify({'error': 'Invalid or expired QR code'}), 400
        
        # Get student
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Process and verify templates
        face_template = process_image_template(face_data)
        finger_template = process_image_template(fingerprint_data)
        
        if not face_template or not finger_template:
            return jsonify({'error': 'Failed to process biometric data'}), 400
        
        # Verify biometrics
        face_match = compare_templates(student.face_template, face_template)
        finger_match = compare_templates(student.fingerprint_template, finger_template)
        
        if not (face_match and finger_match):
            return jsonify({'error': 'Biometric verification failed'}), 401
        
        # Mark attendance
        now = datetime.now()
        status = 'late' if now.hour >= 9 and now.minute > 15 else 'present'
        
        attendance = Attendance(
            student_id=student.id,
            date=now,
            status=status,
            location=location,
            verification_method='face_and_fingerprint'
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Attendance marked successfully',
            'status': status
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def handler(request):
    """Handle requests in Vercel serverless function"""
    return app(request)
