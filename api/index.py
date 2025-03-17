from flask import Flask, jsonify, request, send_file
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
import cv2

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

# Create tables
with app.app_context():
    db.create_all()

def compare_faces(face1, face2, threshold=0.6):
    """Compare two face templates using cosine similarity"""
    try:
        face1_array = np.frombuffer(face1, dtype=np.float32)
        face2_array = np.frombuffer(face2, dtype=np.float32)
        similarity = np.dot(face1_array, face2_array) / (np.linalg.norm(face1_array) * np.linalg.norm(face2_array))
        return similarity > threshold
    except Exception as e:
        return False

def compare_fingerprints(fp1, fp2, threshold=0.7):
    """Compare two fingerprint templates"""
    try:
        fp1_array = np.frombuffer(fp1, dtype=np.uint8)
        fp2_array = np.frombuffer(fp2, dtype=np.uint8)
        similarity = np.sum(fp1_array == fp2_array) / len(fp1_array)
        return similarity > threshold
    except Exception as e:
        return False

@app.route('/health')
def health():
    try:
        db.session.execute('SELECT 1')
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/generate-qr')
def generate_qr():
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
    try:
        data = request.form
        student_id = data.get('student_id')
        name = data.get('name')
        face_data = data.get('face_template')
        fingerprint_data = data.get('fingerprint_template')
        
        if not all([student_id, name, face_data, fingerprint_data]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Create student
        student = Student(
            student_id=student_id,
            name=name,
            face_template=base64.b64decode(face_data),
            fingerprint_template=base64.b64decode(fingerprint_data)
        )
        
        db.session.add(student)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration successful'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
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
        
        # Verify biometrics
        face_match = compare_faces(student.face_template, base64.b64decode(face_data))
        finger_match = compare_fingerprints(student.fingerprint_template, base64.b64decode(fingerprint_data))
        
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
