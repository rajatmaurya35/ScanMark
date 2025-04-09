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
import uuid

# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Initialize storage
if not hasattr(app, 'initialized'):
    # Default admin
    DEFAULT_PASSWORD = 'admin123'
    DEFAULT_ADMIN = {
        'username': 'admin',
        'password': DEFAULT_PASSWORD,
        'created_at': datetime.now().isoformat()
    }
    
    # Initialize persistent storage
    app.config['ADMINS'] = {'admin': DEFAULT_ADMIN}
    app.config['ACTIVE_SESSIONS'] = {'admin': {}}
    app.config['SESSION_RESPONSES'] = {'admin': {}}
    app.config['ATTENDANCE_RECORDS'] = []
    app.initialized = True

# Configure Flask app
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = '/tmp'  # Use /tmp for Vercel

# No need to create directories in serverless environment

# Helper functions for session data
def get_admin_sessions(admin_username):
    return app.config['ACTIVE_SESSIONS'].get(admin_username, {})

def get_session_responses(admin_username, session_id):
    return app.config['SESSION_RESPONSES'].get(admin_username, {}).get(session_id, [])

def add_session_response(admin_username, session_id, response):
    if admin_username not in app.config['SESSION_RESPONSES']:
        app.config['SESSION_RESPONSES'][admin_username] = {}
    if session_id not in app.config['SESSION_RESPONSES'][admin_username]:
        app.config['SESSION_RESPONSES'][admin_username][session_id] = []
    app.config['SESSION_RESPONSES'][admin_username][session_id].append(response)

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
            
        if username in app.config['ADMINS']:
            flash('Username already exists.', 'error')
            return redirect(url_for('admin_register'))
            
        app.config['ADMINS'][username] = {
            'password_hash': hash_password(password),
            'created_at': datetime.now().isoformat()
        }
        
        # Save credentials to file
        save_credentials()
        
        # Initialize admin's session storage
        app.config['ACTIVE_SESSIONS'][username] = {}
        app.config['SESSION_RESPONSES'][username] = {}
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('admin_login'))
        
    return render_template('admin/register.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in app.config['ADMINS'] and password == app.config['ADMINS'][username]['password']:
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
    for session_id, session_data in app.config['ACTIVE_SESSIONS'][admin_username].items():
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
    if admin_username not in app.config['ACTIVE_SESSIONS']:
        app.config['ACTIVE_SESSIONS'][admin_username] = {}
    app.config['ACTIVE_SESSIONS'][admin_username][session_id] = session_data
    
    return jsonify({
        'success': True,
        'session': {
            'id': session_id,
            'qr_code': qr_code,
            'form_url': form_url,
            'name': name
        }
    })

@app.route('/create_session', methods=['POST'])
def create_session():
    if 'admin_username' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    
    admin_username = session['admin_username']
    
    # Get session details from form
    session_name = request.form.get('session_name')
    faculty_name = request.form.get('faculty_name')
    branch = request.form.get('branch')
    semester = request.form.get('semester')
    
    if not all([session_name, faculty_name, branch, semester]):
        return jsonify({'error': 'All fields are required'}), 400
    
    try:
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create session data
        session_data = {
            'name': session_name,
            'faculty': faculty_name,
            'branch': branch,
            'semester': semester,
            'created_at': datetime.now().isoformat(),
            'qr_code': None,
            'form_url': None
        }
        
        # Ensure static directory exists
        os.makedirs('static', exist_ok=True)
        
        # Generate QR code
        form_url = url_for('attendance_form', admin=admin_username, session=session_id, _external=True)
        qr = segno.make(form_url)
        
        # Save QR code with unique filename
        qr_filename = f"qr_{admin_username}_{session_id}.png"
        qr_path = os.path.join('static', qr_filename)
        qr.save(qr_path, scale=10)
        
        # Update session data
        session_data['qr_code'] = qr_filename
        session_data['form_url'] = form_url
        
        # Initialize session storage if needed
        if admin_username not in app.config['ACTIVE_SESSIONS']:
            app.config['ACTIVE_SESSIONS'][admin_username] = {}
            
        if admin_username not in app.config['SESSION_RESPONSES']:
            app.config['SESSION_RESPONSES'][admin_username] = {}
            
        # Store session data
        app.config['ACTIVE_SESSIONS'][admin_username][session_id] = session_data
        app.config['SESSION_RESPONSES'][admin_username][session_id] = []
        
        return jsonify({
            'success': True,
            'message': 'Session created successfully',
            'session_id': session_id,
            'qr_code': qr_filename,
            'form_url': form_url
        })
        
    except Exception as e:
        app.logger.error(f"Error creating session: {str(e)}")
        return jsonify({'error': 'Failed to generate QR code'}), 500

def generate_session_qr(admin_username, session_id, session_data):
    """Generate QR code for a session with pre-filled form fields"""
    if admin_username not in app.config['SESSION_RESPONSES']:
        app.config['SESSION_RESPONSES'][admin_username] = {}
    
    if session_id not in app.config['SESSION_RESPONSES'][admin_username]:
        app.config['SESSION_RESPONSES'][admin_username][session_id] = []
    
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
            active_sessions = get_admin_sessions(admin_username)
            if session_id in active_sessions:
                session_data = active_sessions[session_id]
                # Add session name if not present
                if 'name' not in session_data:
                    session_data['name'] = f'Session {session_id[:8]}'
                return render_template('attendance_form.html', 
                                   session=session_data,
                                   session_id=session_id,
                                   admin_username=admin_username,
                                   show_location=True)
            else:
                return "Session not found", 404
        else:
            return "Invalid parameters", 400
            
    elif request.method == 'POST':
        try:
            # Get form data
            enrollment_no = request.form.get('enrollment_no')
            student_name = request.form.get('student_name')
            session_id = request.form.get('session_id')
            admin_username = request.form.get('admin')
            latitude = request.form.get('latitude')
            longitude = request.form.get('longitude')
            address = request.form.get('address')
            biometric_verified = request.form.get('biometric_verified')
            
            print(f"Received attendance data: {request.form}")
            
            # Validate required fields
            if not all([enrollment_no, student_name, session_id, admin_username]):
                return jsonify({
                    'success': False,
                    'message': 'Please fill in all required fields'
                }), 400
            
            # Validate location
            if not all([latitude, longitude, address]):
                return jsonify({
                    'success': False,
                    'message': 'Location information is required'
                }), 400
            
            # Validate face verification
            if biometric_verified != 'true':
                return jsonify({
                    'success': False,
                    'message': 'Face verification is required'
                }), 400
            
            # Check if session exists and is active
            active_sessions = get_admin_sessions(admin_username)
            if session_id not in active_sessions:
                return jsonify({
                    'success': False,
                    'message': 'Invalid or expired session'
                }), 400
                
            session_data = active_sessions[session_id]
            if not session_data.get('active', False):
                return jsonify({
                    'success': False,
                    'message': 'This session is no longer active'
                }), 400
            
            # Create attendance record
            attendance_data = {
                'enrollment_no': enrollment_no,
                'student_name': student_name,
                'session_id': session_id,
                'admin_username': admin_username,
                'created_at': datetime.now().isoformat(),
                'latitude': latitude,
                'longitude': longitude,
                'address': address,
                'biometric_verified': True,
                'biometric_type': 'Face ID'
            }
            
            # Store attendance data
            add_session_response(admin_username, session_id, attendance_data)
            
            return jsonify({
                'success': True,
                'message': 'Attendance marked successfully!'
            })
                
        except Exception as e:
            print(f"Error in submit_attendance: {str(e)}")
            return jsonify({
                'success': False,
                'message': 'An error occurred. Please try again.'
            }), 500
@app.route('/admin/view-responses/<session_id>')
@login_required
def view_responses(session_id):
    admin_username = session.get('admin_username')
    responses = app.config['SESSION_RESPONSES'].get(admin_username, {}).get(session_id, [])
    session_data = app.config['ACTIVE_SESSIONS'].get(admin_username, {}).get(session_id, {})
    
    # Generate QR code file path
    qr_path = None
    if session_data:  # Only try to handle QR if we have session data
        qr_path = f'static/qr_codes/{session_id}.png'
        if not os.path.exists(qr_path):
            # Generate QR code
            qr_code, _ = generate_session_qr(admin_username, session_id, session_data)
            if qr_code:
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
    responses = app.config['SESSION_RESPONSES'].get(admin_username, {}).get(session_id, [])
    
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
    if session_id in app.config['ACTIVE_SESSIONS'][admin_username]:
        app.config['ACTIVE_SESSIONS'][admin_username][session_id]['active'] = not app.config['ACTIVE_SESSIONS'][admin_username][session_id]['active']
        return jsonify({'success': True, 'active': app.config['ACTIVE_SESSIONS'][admin_username][session_id]['active']})
    return jsonify({'error': 'Session not found'}), 404

@app.route('/admin/delete-session/<session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    admin_username = session['admin_username']
    if session_id in app.config['ACTIVE_SESSIONS'][admin_username]:
        del app.config['ACTIVE_SESSIONS'][admin_username][session_id]
        if session_id in app.config['SESSION_RESPONSES'][admin_username]:
            del app.config['SESSION_RESPONSES'][admin_username][session_id]
        return jsonify({'success': True})
    return jsonify({'error': 'Session not found'}), 404

@app.route('/static/qr_codes/<path:filename>')
def serve_qr(filename):
    try:
        # Get session details from filename
        session_id = filename.split('.')[0]  # Remove .png extension
        admin_username = session.get('admin_username')
        session_data = app.config['ACTIVE_SESSIONS'].get(admin_username, {}).get(session_id, {})
        
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
