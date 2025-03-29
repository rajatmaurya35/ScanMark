from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import secrets
import hashlib
import base64
import segno
from io import BytesIO
from datetime import datetime
from urllib.parse import urlencode
from functools import wraps

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# In-memory storage
ADMINS = {}  # username -> {password_hash, created_at}
ACTIVE_SESSIONS = {}  # admin_username -> {session_id -> session_data}
SESSION_RESPONSES = {}  # admin_username -> {session_id -> [responses]}
ATTENDANCE_RECORDS = []  # Store attendance records with verification data

# Your original form ID - this will be used as a template
TEMPLATE_FORM_ID = '1FAIpQLSdnEVo2O_Ij6cUwtA4tiVOfG_Gb8Gfd9D4QI2St7wBMdiWkMA'

GOOGLE_FORMS = {
    'base_url': 'https://docs.google.com/forms/d/e/',
    'response_url': 'https://docs.google.com/forms/d/e/{form_id}/formResponse'
}

# These are the entry IDs from your form
FORM_FIELDS = {
    'name': 'entry.303339851',          # Student Name
    'student_id': 'entry.451434900',    # Student ID/Roll Number
    'semester': 'entry.771272441',      # Semester
    'branch': 'entry.1785981667',       # Branch
    'session': 'entry.1294673448',      # Subject/Session
    'faculty': 'entry.13279433',        # Faculty Name
    'location': 'entry.2093708733',     # Location
    'timestamp': 'entry.1574315841'     # Timestamp
}

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

def generate_session_qr(admin_username, session_id, session_data):
    """Generate QR code for a session with pre-filled form fields"""
    # Initialize storage for this admin if not exists
    if admin_username not in SESSION_RESPONSES:
        SESSION_RESPONSES[admin_username] = {}
    
    if session_id not in SESSION_RESPONSES[admin_username]:
        SESSION_RESPONSES[admin_username][session_id] = []
    
    # Create a form submission URL
    params = {
        FORM_FIELDS['session']: session_data['name'],
        FORM_FIELDS['faculty']: session_data['faculty'],
        FORM_FIELDS['branch']: session_data['branch'],
        FORM_FIELDS['semester']: session_data['semester'],
        'sessionId': session_id,
        'adminId': admin_username
    }
    
    # Create a local endpoint URL for form submission
    form_url = url_for('submit_attendance', session_id=session_id, admin_id=admin_username, _external=True)
    
    try:
        qr = segno.make(form_url, error='H')
        buffer = BytesIO()
        qr.save(buffer, kind='png', scale=20)
        qr_b64 = base64.b64encode(buffer.getvalue()).decode()
        buffer.close()
        return qr_b64, form_url
    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None, form_url

@app.route('/submit-attendance/<admin_id>/<session_id>', methods=['GET', 'POST'])
def submit_attendance(admin_id, session_id):
    if request.method == 'POST':
        if admin_id not in SESSION_RESPONSES or session_id not in SESSION_RESPONSES[admin_id]:
            return jsonify({'error': 'Invalid session'}), 404
            
        # Get session data
        session_data = ACTIVE_SESSIONS[admin_id][session_id]
        if not session_data['active']:
            return jsonify({'error': 'Session is not active'}), 403
            
        # Record the attendance
        attendance = {
            'student_name': request.form.get('student_name'),
            'student_id': request.form.get('student_id'),
            'timestamp': datetime.now(),
            'session_name': session_data['name'],
            'faculty': session_data['faculty'],
            'branch': session_data['branch'],
            'semester': session_data['semester']
        }
        
        SESSION_RESPONSES[admin_id][session_id].append(attendance)
        return jsonify({'success': True})
        
    # Show the attendance form
    if admin_id in ACTIVE_SESSIONS and session_id in ACTIVE_SESSIONS[admin_id]:
        session_data = ACTIVE_SESSIONS[admin_id][session_id]
        return render_template('attendance_form.html', 
                            session=session_data,
                            admin_id=admin_id,
                            session_id=session_id)
    
    return 'Session not found', 404

@app.route('/submit-attendance', methods=['POST'])
def submit_attendance_verification():
    try:
        student_id = request.form.get('student_id')
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        biometric_verified = request.form.get('biometric_verified') == 'true'
        
        if not all([student_id, latitude, longitude, biometric_verified]):
            return jsonify({
                'success': False,
                'message': 'All verifications (location and biometric) are required'
            }), 400

        # Store attendance with verification data
        attendance_data = {
            'student_id': student_id,
            'latitude': float(latitude),
            'longitude': float(longitude),
            'biometric_verified': biometric_verified,
            'created_at': datetime.now().isoformat()
        }
        
        # Add to your storage (e.g., database)
        ATTENDANCE_RECORDS.append(attendance_data)
        
        return jsonify({
            'success': True,
            'message': 'Attendance marked successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/admin/view-responses/<session_id>')
@login_required
def view_responses(session_id):
    admin_username = session['admin_username']
    if session_id not in ACTIVE_SESSIONS[admin_username]:
        flash('Session not found.', 'error')
        return redirect(url_for('admin_dashboard'))
    
    # Get responses for this session
    responses = SESSION_RESPONSES[admin_username].get(session_id, [])
    session_data = ACTIVE_SESSIONS[admin_username][session_id]
    
    return render_template('admin/view_responses.html',
                         session=session_data,
                         responses=responses)

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

@app.route('/admin/toggle-session/<session_id>', methods=['POST'])
@login_required
def toggle_session(session_id):
    admin_username = session['admin_username']
    if session_id in ACTIVE_SESSIONS[admin_username]:
        ACTIVE_SESSIONS[admin_username][session_id]['active'] = not ACTIVE_SESSIONS[admin_username][session_id]['active']
        return jsonify({'success': True, 'active': ACTIVE_SESSIONS[admin_username][session_id]['active']})
    return jsonify({'error': 'Session not found'}), 404

@app.route('/admin/check-session/<session_id>')
@login_required
def check_session(session_id):
    admin_username = session['admin_username']
    if session_id in ACTIVE_SESSIONS[admin_username]:
        session_data = ACTIVE_SESSIONS[admin_username][session_id]
        return jsonify({
            'active': session_data['active'],
            'form_url': session_data.get('form_url', '')
        })
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
