import os
import json
import secrets
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from io import BytesIO
import qrcode
from config import config

app = Flask(__name__)
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Initialize database
db = SQLAlchemy(app)

class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100))
    registered_on = db.Column(db.DateTime, default=datetime.now)
    attendances = db.relationship('Attendance', backref='student', lazy=True)

class Attendance(db.Model):
    __tablename__ = 'attendances'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='present')
    location = db.Column(db.String(100))

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate-qr', methods=['GET'])
def get_qr_code():
    """Generate new QR code for attendance"""
    try:
        img_io, token, expiry = generate_qr_code()
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
        token_data = request.form.get('token')
        location = request.form.get('location')
        
        if not all([student_id, token_data, location]):
            return jsonify({'error': 'Missing required fields'}), 400
            
        # Verify token and expiry
        if not verify_token(token_data):
            return jsonify({'error': 'Invalid or expired QR code'}), 400
            
        # Basic location validation
        try:
            loc_data = json.loads(location)
            if not (-90 <= float(loc_data['latitude']) <= 90) or not (-180 <= float(loc_data['longitude']) <= 180):
                return jsonify({'error': 'Invalid location coordinates'}), 400
        except:
            return jsonify({'error': 'Invalid location data'}), 400
            
        # Get or create student
        student = Student.query.filter_by(student_id=student_id).first()
        if not student:
            student = Student(student_id=student_id)
            db.session.add(student)
            db.session.commit()
        
        # Record attendance with status based on time
        now = datetime.now()
        status = 'late' if now.hour >= 9 and now.minute > 15 else 'present'
        
        attendance = Attendance(
            student_id=student.id,
            date=now,
            status=status,
            location=location
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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
