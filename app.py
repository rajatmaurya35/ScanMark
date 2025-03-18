import os
import json
import secrets
import base64
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, make_response
from supabase import create_client, Client
from io import BytesIO
import qrcode
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize Supabase client
try:
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("Missing Supabase credentials")
        
    supabase: Client = create_client(supabase_url, supabase_key)
    logger.info("Supabase client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Supabase client: {str(e)}")
    raise

@app.route('/')
def index():
    """Dashboard page"""
    try:
        # Get all students
        students_response = supabase.table('students').select('*').execute()
        if hasattr(students_response, 'error') and students_response.error:
            raise Exception(f"Supabase students query error: {students_response.error}")
        students = students_response.data if students_response.data else []
        
        # Get recent attendances with student info
        attendances_response = supabase.table('attendances')\
            .select('*, students(name)')\
            .order('date', desc=True)\
            .limit(10)\
            .execute()
        if hasattr(attendances_response, 'error') and attendances_response.error:
            raise Exception(f"Supabase attendances query error: {attendances_response.error}")
        attendances = attendances_response.data if attendances_response.data else []
        
        return render_template('dashboard.html', 
                             students=students, 
                             attendances=attendances,
                             now=datetime.now())
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/scan')
def scan():
    """QR code scanning page"""
    try:
        return render_template('scan.html')
    except Exception as e:
        logger.error(f"Error rendering scan page: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/generate-qr', methods=['GET'])
def get_qr_code():
    """Generate QR code with improved error handling"""
    try:
        # Generate token with 5-minute expiry
        token = secrets.token_urlsafe(32)
        expiry = datetime.now() + timedelta(minutes=5)
        
        # Save token to Supabase
        token_response = supabase.table('qr_tokens').insert({
            'token': token,
            'expiry': expiry.isoformat(),
            'created_at': datetime.now().isoformat()
        }).execute()
        
        if hasattr(token_response, 'error') and token_response.error:
            raise Exception(f"Failed to save token: {token_response.error}")
        
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
        logger.error(f"QR generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/register', methods=['POST'])
def register_student():
    """Register student with improved validation"""
    try:
        data = request.get_json() if request.is_json else request.form
        student_id = data.get('student_id')
        name = data.get('name')
        
        # Validate required fields
        if not all([student_id, name]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if student already exists
        existing_response = supabase.table('students')\
            .select('*')\
            .eq('student_id', student_id)\
            .execute()
            
        if hasattr(existing_response, 'error') and existing_response.error:
            raise Exception(f"Failed to check existing student: {existing_response.error}")
            
        if existing_response.data:
            return jsonify({'error': 'Student ID already exists'}), 400
        
        # Create new student
        new_student_response = supabase.table('students').insert({
            'student_id': student_id,
            'name': name,
            'registered_on': datetime.now().isoformat()
        }).execute()
        
        if hasattr(new_student_response, 'error') and new_student_response.error:
            raise Exception(f"Failed to create student: {new_student_response.error}")
        
        return jsonify({'message': 'Student registered successfully'}), 201
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/mark-attendance', methods=['POST'])
def mark_attendance():
    """Mark attendance with comprehensive validation"""
    try:
        data = request.get_json() if request.is_json else request.form
        student_id = data.get('student_id')
        location = data.get('location', 'Unknown')
        
        # Validate required fields
        if not student_id:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Get student
        student_response = supabase.table('students')\
            .select('*')\
            .eq('student_id', student_id)\
            .execute()
            
        if hasattr(student_response, 'error') and student_response.error:
            raise Exception(f"Failed to fetch student: {student_response.error}")
            
        if not student_response.data:
            return jsonify({'error': 'Student not found'}), 404
            
        student = student_response.data[0]
        
        # Check for duplicate attendance
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        existing_response = supabase.table('attendances')\
            .select('*')\
            .eq('student_id', student['id'])\
            .gte('date', today.isoformat())\
            .execute()
            
        if hasattr(existing_response, 'error') and existing_response.error:
            raise Exception(f"Failed to check existing attendance: {existing_response.error}")
            
        if existing_response.data:
            return jsonify({'error': 'Attendance already marked for today'}), 400
        
        # Mark attendance
        attendance_response = supabase.table('attendances').insert({
            'student_id': student['id'],
            'date': datetime.now().isoformat(),
            'status': 'present',
            'location': location
        }).execute()
        
        if hasattr(attendance_response, 'error') and attendance_response.error:
            raise Exception(f"Failed to mark attendance: {attendance_response.error}")
        
        return jsonify({
            'message': 'Attendance marked successfully',
            'student_name': student['name'],
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.error(f"Attendance marking error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    logger.error(f"404 error: {str(error)}")
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {str(error)}")
    return jsonify({'error': str(error)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
