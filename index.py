from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
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

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# In-memory storage
ADMINS = {}  # username -> {password_hash, created_at}
ACTIVE_SESSIONS = {}  # admin_username -> {session_id -> session_data}
SESSION_RESPONSES = {}  # admin_username -> {session_id -> [responses]}
ATTENDANCE_RECORDS = []  # Store attendance records with verification data

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
            'created_at': datetime.now()
        }
        
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

        # Prepare attendance data
        attendance_data = {
            'student_id': student_id,
            'student_name': student_name,
            'latitude': float(latitude),
            'longitude': float(longitude),
            'biometric_verified': biometric_verified,
            'biometric_type': biometric_type,
            'session_name': session_data['name'],
            'faculty': session_data['faculty'],
            'branch': session_data['branch'],
            'semester': session_data['semester'],
            'created_at': datetime.now().isoformat()
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
    
    return render_template('admin/view_responses.html', 
                         responses=responses,
                         session=session_data,
                         session_id=session_id)

@app.route('/admin/download-responses/<session_id>')
@login_required
def download_responses(session_id):
    admin_username = session.get('admin_username')
    responses = SESSION_RESPONSES.get(admin_username, {}).get(session_id, [])
    
    if not responses:
        return "No responses found", 404
        
    # Create CSV content
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Student ID', 'Time', 'Biometric Type', 
                    'Location (Lat, Long)'])
    
    for resp in responses:
        writer.writerow([
            resp['student_name'],
            resp['student_id'],
            resp['created_at'],
            resp['biometric_type'],
            f"{resp['latitude']}, {resp['longitude']}"
        ])
    
    # Create response
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=responses_{session_id}.csv'
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

if __name__ == '__main__':
    app.run(debug=True)
