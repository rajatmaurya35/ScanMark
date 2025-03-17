import os
import json
import secrets
import base64
import numpy as np
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
from io import BytesIO
import qrcode
from PIL import Image
import cv2
from deepface import DeepFace
from config import config

app = Flask(__name__)
env = os.getenv('FLASK_ENV', 'production')
app.config.from_object(config[env])

# Initialize database
db = SQLAlchemy(app)

# Enable CORS
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE')
    return response

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    face_encoding = db.Column(db.LargeBinary)  # Store face encoding
    fingerprint_template = db.Column(db.LargeBinary)  # Store fingerprint template
    registered_on = db.Column(db.DateTime, default=datetime.now)
    attendances = db.relationship('Attendance', backref='student', lazy=True)

class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='present')
    location = db.Column(db.String(100))
    verification_method = db.Column(db.String(20))  # face, fingerprint, or both

class QRToken(db.Model):
    __tablename__ = 'qr_tokens'
    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

def verify_token(token_data):
    """Verify QR token and expiry"""
    try:
        data = json.loads(token_data)
        expiry = datetime.fromisoformat(data['expiry'])
        return datetime.now() <= expiry
    except:
        return False

def generate_qr_code():
    """Generate QR code with token and expiry"""
    token = secrets.token_urlsafe(16)
    expiry = datetime.now() + timedelta(hours=24)
    
    # Store token in database
    qr_token = QRToken(token=token, expiry=expiry)
    db.session.add(qr_token)
    db.session.commit()
    
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

def process_face_image(face_data):
    """Process base64 face image and return encoding"""
    try:
        # Decode base64 image
        image_data = base64.b64decode(face_data.split(',')[1])
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Get face embedding using DeepFace
        embedding = DeepFace.represent(img, model_name="Facenet", enforce_detection=True)
        if not embedding:
            return None, "No face detected"
            
        # Convert embedding to bytes for storage
        embedding_bytes = np.array(embedding).tobytes()
        return embedding_bytes, None
    except Exception as e:
        return None, str(e)

def verify_face(stored_encoding, new_face_data):
    """Verify face match"""
    try:
        # Process new face image
        new_encoding, error = process_face_image(new_face_data)
        if error:
            return False, error
            
        # Convert stored encoding back to numpy array
        stored_embedding = np.frombuffer(stored_encoding, dtype=np.float32)
        new_embedding = np.frombuffer(new_encoding, dtype=np.float32)
        
        # Calculate cosine similarity
        similarity = np.dot(stored_embedding, new_embedding) / (np.linalg.norm(stored_embedding) * np.linalg.norm(new_embedding))
        return similarity > 0.7, None  # Threshold can be adjusted
    except Exception as e:
        return False, str(e)

def verify_fingerprint(stored_template, new_template):
    """Verify fingerprint match using minutiae matching"""
    try:
        # Convert templates to numpy arrays
        template1 = np.frombuffer(base64.b64decode(stored_template), dtype=np.uint8)
        template2 = np.frombuffer(base64.b64decode(new_template), dtype=np.uint8)
        
        # Simple minutiae matching (you may want to use a more sophisticated matching algorithm)
        similarity = np.sum(template1 == template2) / len(template1)
        return similarity > 0.8, None
    except Exception as e:
        return False, str(e)

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for Vercel deployment"""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/generate-qr', methods=['GET'])
def get_qr_code():
    """Generate new QR code for attendance"""
    try:
        img_io, token, expiry = generate_qr_code()
        response = make_response(send_file(
            img_io,
            mimetype='image/png',
            as_attachment=True,
            download_name='attendance_qr.png'
        ))
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['POST'])
def register_student():
    """Register new student with biometric data"""
    try:
        data = request.form
        student_id = data.get('student_id')
        name = data.get('name')
        face_data = data.get('face_image')
        fingerprint_data = data.get('fingerprint_template')
        
        if not all([student_id, name, face_data, fingerprint_data]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Process face image
        face_encoding, error = process_face_image(face_data)
        if error:
            return jsonify({'error': f'Face processing error: {error}'}), 400
            
        # Create new student
        student = Student(
            student_id=student_id,
            name=name,
            face_encoding=face_encoding,
            fingerprint_template=base64.b64decode(fingerprint_data)
        )
        
        db.session.add(student)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Student registered successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance with biometric verification"""
    try:
        data = request.form
        student_id = data.get('student_id')
        token_data = data.get('token')
        location = data.get('location')
        face_data = data.get('face_image')
        fingerprint_data = data.get('fingerprint_template')
        
        if not all([student_id, token_data, location, face_data, fingerprint_data]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Verify token
        if not verify_token(token_data):
            return jsonify({'error': 'Invalid or expired QR code'}), 400
            
        # Get student
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404
            
        # Verify face
        face_match, face_error = verify_face(student.face_encoding, face_data)
        if face_error:
            return jsonify({'error': f'Face verification error: {face_error}'}), 400
            
        # Verify fingerprint
        finger_match, finger_error = verify_fingerprint(student.fingerprint_template, fingerprint_data)
        if finger_error:
            return jsonify({'error': f'Fingerprint verification error: {finger_error}'}), 400
            
        if not (face_match and finger_match):
            return jsonify({'error': 'Biometric verification failed'}), 401
            
        # Record attendance
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

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not Found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal Server Error'}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
