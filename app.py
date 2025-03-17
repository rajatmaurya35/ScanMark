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

# Configure the Flask app
env = os.getenv('FLASK_ENV', 'production')
app.config.from_object(config[env])

# Initialize SQLAlchemy after app configuration
db = SQLAlchemy(app)

# Create tables within app context
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {str(e)}")

# Enable CORS and set headers
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
    face_encoding = db.Column(db.LargeBinary)
    fingerprint_template = db.Column(db.LargeBinary)
    registered_on = db.Column(db.DateTime, default=datetime.now)
    attendances = db.relationship('Attendance', backref='student', lazy=True)

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

def process_face_image(face_data):
    """Process face image with error handling and retries"""
    try:
        # Remove data URL prefix if present
        if ',' in face_data:
            face_data = face_data.split(',')[1]
        
        # Decode base64 image
        image_data = base64.b64decode(face_data)
        nparr = np.frombuffer(image_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Convert BGR to RGB (DeepFace expects RGB)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Get face embedding
        embedding = DeepFace.represent(img, model_name="Facenet", enforce_detection=True)
        if not embedding:
            return None, "No face detected"
        
        # Convert embedding to bytes
        embedding_bytes = np.array(embedding).tobytes()
        return embedding_bytes, None
    except Exception as e:
        return None, f"Face processing error: {str(e)}"

def verify_face(stored_encoding, new_face_data, threshold=0.7):
    """Verify face match with improved error handling"""
    try:
        # Process new face image
        new_encoding, error = process_face_image(new_face_data)
        if error:
            return False, error
        
        # Convert stored encoding back to numpy array
        stored_embedding = np.frombuffer(stored_encoding, dtype=np.float32)
        new_embedding = np.frombuffer(new_encoding, dtype=np.float32)
        
        # Calculate cosine similarity
        similarity = np.dot(stored_embedding, new_embedding) / (
            np.linalg.norm(stored_embedding) * np.linalg.norm(new_embedding)
        )
        return similarity > threshold, None
    except Exception as e:
        return False, f"Face verification error: {str(e)}"

def verify_fingerprint(stored_template, new_template, threshold=0.8):
    """Verify fingerprint match with improved error handling"""
    try:
        # Convert templates to numpy arrays
        template1 = np.frombuffer(base64.b64decode(stored_template), dtype=np.uint8)
        template2 = np.frombuffer(base64.b64decode(new_template), dtype=np.uint8)
        
        # Calculate similarity
        similarity = np.sum(template1 == template2) / len(template1)
        return similarity > threshold, None
    except Exception as e:
        return False, f"Fingerprint verification error: {str(e)}"

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint"""
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
    """Generate QR code with improved error handling"""
    try:
        # Generate token with 5-minute expiry
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(minutes=5)
        
        # Save token
        qr_token = QRToken(token=token, expiry=expiry)
        db.session.add(qr_token)
        db.session.commit()
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(json.dumps({
            'token': token,
            'expiry': expiry.isoformat()
        }))
        qr.make(fit=True)
        
        # Create QR image
        img = qr.make_image(fill_color="black", back_color="white")
        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)
        
        response = make_response(send_file(
            img_io,
            mimetype='image/png',
            as_attachment=True,
            download_name='attendance_qr.png'
        ))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        return response
    except Exception as e:
        return jsonify({'error': f"QR generation error: {str(e)}"}), 500

@app.route('/register', methods=['POST'])
def register_student():
    """Register student with improved validation"""
    try:
        data = request.form
        student_id = data.get('student_id')
        name = data.get('name')
        face_data = data.get('face_image')
        fingerprint_data = data.get('fingerprint_template')
        
        # Validate required fields
        if not all([student_id, name, face_data, fingerprint_data]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if student already exists
        existing_student = Student.query.filter_by(student_id=student_id).first()
        if existing_student:
            return jsonify({'error': 'Student ID already registered'}), 409
        
        # Process face image
        face_encoding, error = process_face_image(face_data)
        if error:
            return jsonify({'error': error}), 400
        
        # Create student
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
            'message': 'Registration successful',
            'student_id': student_id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Registration error: {str(e)}"}), 500

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance with comprehensive validation"""
    try:
        data = request.form
        student_id = data.get('student_id')
        token = data.get('token')
        location = data.get('location')
        face_data = data.get('face_image')
        fingerprint_data = data.get('fingerprint_template')
        
        # Validate required fields
        if not all([student_id, token, location, face_data, fingerprint_data]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Verify QR token
        qr_token = QRToken.query.filter_by(token=token).first()
        if not qr_token:
            return jsonify({'error': 'Invalid QR token'}), 401
        if qr_token.expiry < datetime.now():
            return jsonify({'error': 'QR token expired'}), 401
        
        # Get student
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            return jsonify({'error': 'Student not found'}), 404
        
        # Verify face
        face_match, face_error = verify_face(student.face_encoding, face_data)
        if face_error:
            return jsonify({'error': face_error}), 400
        if not face_match:
            return jsonify({'error': 'Face verification failed'}), 401
        
        # Verify fingerprint
        finger_match, finger_error = verify_fingerprint(
            student.fingerprint_template,
            fingerprint_data
        )
        if finger_error:
            return jsonify({'error': finger_error}), 400
        if not finger_match:
            return jsonify({'error': 'Fingerprint verification failed'}), 401
        
        # Determine attendance status
        now = datetime.now()
        status = 'late' if now.hour >= 9 and now.minute > 15 else 'present'
        
        # Record attendance
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
            'status': status,
            'timestamp': now.isoformat()
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f"Attendance marking error: {str(e)}"}), 500

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    # Get port from environment variable for Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
