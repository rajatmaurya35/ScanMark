from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response, send_file
import os
import secrets
import hashlib
import base64
import segno
from io import BytesIO
from datetime import datetime
from urllib.parse import urlencode
from functools import wraps
import csv
from io import StringIO
import json
from pathlib import Path

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Create required directories
for path in ['static/uploads', 'static/qr_codes']:
    Path(path).mkdir(parents=True, exist_ok=True)

# Load credentials from file
def load_credentials():
    try:
        with open('credentials.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_credentials(data):
    with open('credentials.json', 'w') as f:
        json.dump(data, f, indent=4)

# Initialize storage
ADMINS = load_credentials()  # username -> {password_hash, created_at}
ACTIVE_SESSIONS = {}  # admin_username -> {session_id -> session_data}
# Use app-level storage instead of global variables
def get_session_responses():
    return app.response_data

def set_session_response(admin_username, session_id, response):
    if admin_username not in app.response_data:
        app.response_data[admin_username] = {}
    if session_id not in app.response_data[admin_username]:
        app.response_data[admin_username][session_id] = []
    app.response_data[admin_username][session_id].append(response)  # admin_username -> {session_id -> [responses]}
ATTENDANCE_RECORDS = []  # Store attendance records with verification data

# Initialize sessions for existing admins
for username in ADMINS:
    ACTIVE_SESSIONS[username] = {}
    SESSION_RESPONSES[username] = {}

def hash_password(password):
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return base64.b64encode(salt + key).decode('utf-8')

def verify_password(password, hashed):
    decoded = base64.b64decode(hashed.encode('utf-8'))
    salt, key = decoded[:32], decoded[32:]
    new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return new_key == key

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_username' not in session:
            flash('Please log in first.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return redirect(url_for('admin_login'))

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('admin_register'))
            
        if username in ADMINS:
            flash('Username already exists.', 'error')
            return redirect(url_for('admin_register'))
            
        ADMINS[username] = {
            'password_hash': hash_password(password),
            'created_at': datetime.now().isoformat()
        }
        
        # Save credentials to file
        save_credentials(ADMINS)
        
        # Initialize admin's session storage
        ACTIVE_SESSIONS[username] = {}
        SESSION_RESPONSES[username] = {}
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('admin_login'))
        
    return render_template('admin/register.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in ADMINS and verify_password(password, ADMINS[username]['password_hash']):
            session['admin_username'] = username
            return redirect(url_for('admin_dashboard'))
            
        flash('Invalid username or password.', 'error')
        
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_username', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    admin_username = session['admin_username']
    active_sessions = []
    
    # Get only this admin's sessions
    for session_id, session_data in ACTIVE_SESSIONS[admin_username].items():
        # Regenerate QR if not present
        if 'qr_code' not in session_data or not session_data['qr_code']:
            qr_code, form_url = generate_session_qr(admin_username, session_id, session_data)
            session_data['qr_code'] = qr_code
            session_data['form_url'] = form_url
            
        active_sessions.append({
            'id': session_id,
            'name': session_data['name'],
            'faculty': session_data['faculty'],
            'branch': session_data['branch'],
            'semester': session_data['semester'],
            'created_at': session_data['created_at'],
            'active': session_data['active'],
            'qr_code': session_data['qr_code'],
            'form_url': session_data['form_url']
        })
        
    return render_template('admin/dashboard.html', sessions=active_sessions)

@app.route('/admin/generate-qr', methods=['POST'])
@login_required
def generate_qr():
    admin_username = session['admin_username']
    name = request.form.get('name')
    faculty = request.form.get('faculty')
    branch = request.form.get('branch')
    semester = request.form.get('semester')
    
    if not all([name, faculty, branch, semester]):
        return jsonify({'error': 'All fields are required'}), 400
        
    session_id = secrets.token_urlsafe(16)
    session_data = {
        'name': name,
        'faculty': faculty,
        'branch': branch,
        'semester': semester,
        'created_at': datetime.now(),
        'active': True
    }
    
    qr_code, form_url = generate_session_qr(admin_username, session_id, session_data)
    if not qr_code:
        return jsonify({'error': 'Failed to generate QR code'}), 500
        
    session_data['qr_code'] = qr_code
    session_data['form_url'] = form_url
    
    # Store in admin's sessions
    if admin_username not in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS[admin_username] = {}
    ACTIVE_SESSIONS[admin_username][session_id] = session_data
    
    return jsonify({
        'success': True,
        'session': {
            'id': session_id,
            'qr_code': qr_code,
            'form_url': form_url,
            'name': name
        }
    })

def generate_session_qr(admin_username, session_id, session_data):
    """Generate QR code for a session with pre-filled form fields"""
    if admin_username not in SESSION_RESPONSES:
        SESSION_RESPONSES[admin_username] = {}
    
    if session_id not in SESSION_RESPONSES[admin_username]:
        SESSION_RESPONSES[admin_username][session_id] = []
    
    try:
        # Generate attendance form URL with proper parameters
        base_url = request.host_url.rstrip('/')
        form_url = f"{base_url}/submit-attendance?admin={admin_username}&session_id={session_id}"
        
        # Generate QR code
        qr = segno.make(form_url)
        
        # Save QR code to a BytesIO object
        qr_io = BytesIO()
        qr.save(qr_io, kind='png', scale=10)
        qr_io.seek(0)
        
        # Convert to base64
        qr_base64 = base64.b64encode(qr_io.getvalue()).decode()
        
        return qr_base64, form_url
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None, None

@app.route('/submit-attendance', methods=['GET', 'POST'])
def submit_attendance():
    if request.method == 'GET':
        # Show the attendance form
        session_id = request.args.get('session_id')
        admin_username = request.args.get('admin')
        
        if admin_username and session_id:
            if admin_username in ACTIVE_SESSIONS and session_id in ACTIVE_SESSIONS[admin_username]:
                session_data = ACTIVE_SESSIONS[admin_username][session_id]
                return render_template('attendance_form.html', 
                                    session=session_data,
                                    admin_username=admin_username,
                                    session_id=session_id)
        return 'Invalid session', 404

    # Handle POST request
    try:
        # Get form data
        student_id = request.form.get('student_id')
        student_name = request.form.get('student_name')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        biometric_verified = request.form.get('biometric_verified') == 'true'
        biometric_type = request.form.get('biometric_type', 'Biometric')
        admin_username = request.form.get('admin')
        session_id = request.form.get('session_id')

        # Validate required fields
        if not all([student_id, student_name, latitude, longitude, biometric_verified, admin_username, session_id]):
            return jsonify({
                'success': False,
                'message': 'All fields and verifications are required'
            }), 400

        # Check if session exists and is active
        if admin_username not in ACTIVE_SESSIONS or session_id not in ACTIVE_SESSIONS[admin_username]:
            return jsonify({
                'success': False,
                'message': 'Session not found'
            }), 404

        session_data = ACTIVE_SESSIONS[admin_username][session_id]
        if not session_data.get('active', False):
            return jsonify({
                'success': False,
                'message': 'Session is not active'
            }), 403

        # Handle image upload
        image_path = None
        if 'captured_image' in request.files:
            try:
                image = request.files['captured_image']
                if image and image.filename:
                    # Create a unique filename using timestamp and student ID
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f'capture_{student_id}_{timestamp}.jpg'
                    
                    # Ensure uploads directory exists
                    upload_dir = os.path.join('static', 'uploads')
                    os.makedirs(upload_dir, exist_ok=True)
                    
                    # Save the image
                    full_path = os.path.join(upload_dir, filename)
                    image.save(full_path)
                    image_path = f'uploads/{filename}'
                    print(f'Image saved to: {full_path}')
            except Exception as e:
                print(f'Error saving image: {str(e)}')

        # Prepare attendance data with proper location formatting
        attendance_data = {
            'student_name': student_name,
            'student_id': student_id,
            'created_at': datetime.now().isoformat(),
            'latitude': float(latitude),  # Convert to float for map display
            'longitude': float(longitude),  # Convert to float for map display
            'biometric_verified': biometric_verified,
            'biometric_type': biometric_type,
            'image_path': image_path,
            'session_name': session_data['name'],
            'faculty': session_data['faculty'],
            'branch': session_data['branch'],
            'semester': session_data['semester']
        }

        # Store attendance
        if admin_username not in SESSION_RESPONSES:
            SESSION_RESPONSES[admin_username] = {}
        if session_id not in SESSION_RESPONSES[admin_username]:
            SESSION_RESPONSES[admin_username][session_id] = []
        
        SESSION_RESPONSES[admin_username][session_id].append(attendance_data)
        
        return jsonify({
            'success': True,
            'message': 'Attendance marked successfully'
        })
            
    except Exception as e:
        print(f"Error in submit_attendance: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred while marking attendance'
        }), 500

@app.route('/admin/view-responses/<session_id>')
@login_required
def view_responses(session_id):
    admin_username = session.get('admin_username')
    responses = SESSION_RESPONSES.get(admin_username, {}).get(session_id, [])
    session_data = ACTIVE_SESSIONS.get(admin_username, {}).get(session_id, {})
    
    # Generate QR code file path
    qr_path = None
    if session_data:  # Only try to handle QR if we have session data
        qr_path = f'static/qr_codes/{session_id}.png'
        if not os.path.exists(qr_path):
            # Generate QR code
            qr_code, _ = generate_session_qr(admin_username, session_id, session_data)
            if qr_code:
                # Save QR code
                try:
                    qr_data = base64.b64decode(qr_code.split(',')[1])
                    os.makedirs('static/qr_codes', exist_ok=True)
                    with open(qr_path, 'wb') as f:
                        f.write(qr_data)
                except Exception as e:
                    print(f"Error saving QR code: {str(e)}")
                    qr_path = None
    
    return render_template('admin/view_responses.html', 
                         responses=responses,
                         session=session_data,
                         session_id=session_id,
                         qr_path=qr_path)

@app.route('/admin/download-responses/<session_id>')
@login_required
def download_responses(session_id):
    admin_username = session.get('admin_username')
    responses = SESSION_RESPONSES.get(admin_username, {}).get(session_id, [])
    
    if not responses:
        flash('No responses found for this session.', 'warning')
        return redirect(url_for('view_responses', session_id=session_id))
        
    # Create CSV content
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Student ID', 'Time', 'Biometric Type', 
                    'Location (Lat, Long)', 'Image Path'])
    
    for resp in responses:
        writer.writerow([
            resp.get('student_name', ''),
            resp.get('student_id', ''),
            resp.get('created_at', ''),
            resp.get('biometric_type', ''),
            f"{resp.get('latitude', '')}, {resp.get('longitude', '')}",
            resp.get('image_path', '')
        ])
    
    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=responses_{session_id}.csv',
            'Content-Type': 'text/csv; charset=utf-8'
        }
    )

@app.route('/admin/toggle-session/<session_id>', methods=['POST'])
@login_required
def toggle_session(session_id):
    admin_username = session['admin_username']
    if session_id in ACTIVE_SESSIONS[admin_username]:
        ACTIVE_SESSIONS[admin_username][session_id]['active'] = not ACTIVE_SESSIONS[admin_username][session_id]['active']
        return jsonify({'success': True, 'active': ACTIVE_SESSIONS[admin_username][session_id]['active']})
    return jsonify({'error': 'Session not found'}), 404

@app.route('/admin/delete-session/<session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    admin_username = session['admin_username']
    if session_id in ACTIVE_SESSIONS[admin_username]:
        del ACTIVE_SESSIONS[admin_username][session_id]
        if session_id in SESSION_RESPONSES[admin_username]:
            del SESSION_RESPONSES[admin_username][session_id]
        return jsonify({'success': True})
    return jsonify({'error': 'Session not found'}), 404

@app.route('/static/qr_codes/<path:filename>')
def serve_qr(filename):
    try:
        # Get session details from filename
        session_id = filename.split('.')[0]  # Remove .png extension
        admin_username = session.get('admin_username')
        session_data = ACTIVE_SESSIONS.get(admin_username, {}).get(session_id, {})
        
        # Set custom filename with session details
        custom_filename = f"{session_data.get('name', 'session')}_qr.png"
        
        return send_file(
            f'static/qr_codes/{filename}', 
            mimetype='image/png',
            as_attachment=True,
            download_name=custom_filename
        )
    except Exception as e:
        print(f"Error serving QR code: {str(e)}")
        return "QR code not found", 404

@app.route('/static/uploads/<path:filename>')
def serve_image(filename):
    try:
        return send_file(f'static/uploads/{filename}', mimetype='image/jpeg')
    except Exception as e:
        print(f"Error serving image: {str(e)}")
        return "Image not found", 404

if __name__ == '__main__':
    app.run(debug=True)
