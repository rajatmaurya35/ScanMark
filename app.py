from flask import Flask, render_template, request, redirect, session, jsonify, flash, url_for
from collections import Counter
from flask_talisman import Talisman
from flask_session import Session
import os
import secrets
import uuid
import base64
import segno
import io
from io import BytesIO
from datetime import datetime, timedelta, timezone
from functools import wraps
# Custom Supabase implementation using requests
import requests
import json

def create_client(supabase_url, supabase_key):
    class SupabaseClient:
        def __init__(self, url, key):
            self.url = url
            self.key = key
            self.headers = {
                'apikey': key,
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json'
            }
        
        def table(self, table_name):
            class Table:
                def __init__(self, url, headers, table):
                    self.url = url
                    self.headers = headers
                    self.table = table
                    self.base_url = f"{url}/rest/v1"
                
                def select(self, *columns):
                    self.select_columns = ','.join(columns) if columns else '*'
                    return self
                
                def insert(self, data, upsert=False):
                    url = f"{self.base_url}/{self.table}"
                    params = {'prefer': 'return=representation'}
                    if upsert:
                        params['on_conflict'] = 'id'
                    response = requests.post(url, headers=self.headers, params=params, json=data)
                    return response.json()
                
                def update(self, data):
                    url = f"{self.base_url}/{self.table}"
                    params = {'prefer': 'return=representation'}
                    response = requests.patch(url, headers=self.headers, params=params, json=data)
                    return response.json()
                
                def delete(self):
                    url = f"{self.base_url}/{self.table}"
                    params = {'prefer': 'return=representation'}
                    response = requests.delete(url, headers=self.headers, params=params)
                    return response.json()
                
                def eq(self, column, value):
                    self.filter_column = column
                    self.filter_value = value
                    return self
                
                def execute(self):
                    url = f"{self.base_url}/{self.table}"
                    params = {'select': self.select_columns}
                    if hasattr(self, 'filter_column') and hasattr(self, 'filter_value'):
                        params[self.filter_column] = f'eq.{self.filter_value}'
                    response = requests.get(url, headers=self.headers, params=params)
                    return response.json()
            
            return Table(self.url, self.headers, table_name)
    
    return SupabaseClient(supabase_url, supabase_key)
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask, render_template, request, redirect, session, jsonify, flash
import csv
import logging

# Initialize Flask app
app = Flask(__name__)
app.url_map.strict_slashes = False  # allow routes with or without trailing slash
app.logger.setLevel(logging.DEBUG)

@app.before_first_request
def log_routes():
    routes = '\n'.join(str(rule) for rule in app.url_map.iter_rules())
    app.logger.debug(f"Available routes:\n{routes}")
    # Routes will also be accessible via /routes for quick debugging

@app.route('/routes', strict_slashes=False)
def list_routes():
    """Return a JSON list of all URL rules"""
    return jsonify([str(rule) for rule in app.url_map.iter_rules()])

@app.route('/admin/register', strict_slashes=False, methods=['GET', 'POST'])
@app.route('/signup', methods=['GET','POST'], strict_slashes=False)
@app.route('/signup/', methods=['GET','POST'], strict_slashes=False)
def admin_register():
    # Debug logging
    app.logger.info(f"Signup route accessed: {request.method} {request.path}")
    app.logger.info(f"Request headers: {dict(request.headers)}")
    
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        username = request.form.get('username')
        password = request.form.get('password')
        app.logger.info(f"Signup attempt for username: {username}")
        
        # Validate input
        if not username or not password:
            if is_ajax:
                return jsonify({'success': False, 'error': 'Username and password required'})
            flash('Username and password required', 'danger')
            return redirect(url_for('admin_register'))
            
        # Check if username already exists
        try:
            existing_user = supabase.table('admins').select('username').eq('username', username).execute()
            if existing_user.data:
                if is_ajax:
                    return jsonify({'success': False, 'error': 'Username already exists'})
                flash('Username already exists', 'danger')
                return redirect(url_for('admin_register'))
        except Exception as e:
            app.logger.error(f"Error checking username: {e}")
        
        password_hash = generate_password_hash(password)
        
        try:
            app.logger.info("Attempting to create new user in database")
            supabase.table('admins').insert({
                'username': username,
                'password_hash': password_hash,
                'created_at': datetime.now(timezone.utc).isoformat()
            }).execute()
            
            app.logger.info(f"Successfully registered user: {username}")
            
            if is_ajax:
                return jsonify({'success': True, 'redirect': '/admin/login'})
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('admin_login'))
        except Exception as e:
            app.logger.error(f"Registration error: {e}")
            if is_ajax:
                return jsonify({'success': False, 'error': str(e)})
            flash(f'Registration error: {e}', 'danger')
            return redirect(url_for('admin_register'))
    
    # For GET requests, render the signup form
    app.logger.info("Rendering signup form")
    return render_template('signup.html')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'flask_session')
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Enforce HTTPS and secure headers
Talisman(app, content_security_policy=None)

# Initialize Supabase client
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://aaluawvcohqfhevkdnuv.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhbHVhd3Zjb2hxZmhldmtkbnV2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNzY3MzcsImV4cCI6MjA1Nzg1MjczN30.kKL_B4sw1nwY6lbzgyPHQYoC_uqDsPkT51ZOnhr6MNA')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Create tables if they don't exist
def init_db():
    try:
        # Create qr_tokens table
        try:
            # Try to select from qr_tokens table
            result = supabase.table('qr_tokens').select('*').limit(1).execute()
            print("qr_tokens table exists")
        except Exception:
            print("qr_tokens table missing; please create it in Supabase.")
        
        # Create attendance table
        try:
            result = supabase.table('attendance').select('*').limit(1).execute()
            print("attendance table exists")
        except Exception:
            print("attendance table missing; please create it in Supabase.")
        
        # Create admins table
        try:
            result = supabase.table('admins').select('*').limit(1).execute()
            print("admins table exists")
        except Exception as e:
            print(f"Creating admins table: {e}")
            try:
                supabase.table('admins').insert({
                    'username': 'dummy',
                    'password_hash': 'dummy',
                    'created_at': datetime.now().isoformat()
                }).execute()
                # Delete the dummy record
                supabase.table('admins').delete().eq('username', 'dummy').execute()
            except Exception as e:
                print(f"Error creating admins table: {e}")
                pass
        
    except Exception as e:
        print(f"Database initialization error: {e}")

# Initialize database
init_db()

# Ensure the session directory exists
os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)

# Initialize Flask-Session
Session(app)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin' not in session:
            return redirect('/admin/login')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('admin/login.html')

@app.route('/test', strict_slashes=False)
def test():
    return 'Test OK', 200

@app.route('/admin/login', methods=['GET', 'POST'])
@app.route('/admin/login/', methods=['GET', 'POST'])
def admin_login():
    if 'admin' in session:
        return redirect('/admin/dashboard')
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            if is_ajax:
                return jsonify({'success': False, 'error': 'Please enter both username and password'})
            flash('Please enter both username and password', 'danger')
            return redirect('/admin/login')
        try:
            res = supabase.table('admins').select('*').eq('username', username).execute()
            if res.data and check_password_hash(res.data[0]['password_hash'], password):
                session.permanent = True
                session['admin'] = username
                if is_ajax:
                    return jsonify({'success': True, 'redirect': '/admin/dashboard'})
                return redirect('/admin/dashboard')
            # invalid credentials
            if is_ajax:
                return jsonify({'success': False, 'error': 'Invalid username or password'})
            flash('Invalid username or password', 'danger')
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            if is_ajax:
                return jsonify({'success': False, 'error': 'An error occurred during login'})
            flash('An error occurred during login', 'danger')
        return redirect('/admin/login')
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect('/admin/login')

@app.route('/admin/dashboard')
@app.route('/admin/dashboard/')
@login_required
def admin_dashboard():
    try:
        # Fetch all QR tokens ordered by creation
        res = supabase.table('qr_tokens')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()
        tokens = res.data or []
        now = datetime.now(timezone.utc)
        sessions_list = []
        for t in tokens:
            try:
                expires = datetime.fromisoformat(t['expires_at'].replace('Z', '+00:00'))
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                is_active = expires > now
                parts = t['session'].split(' - ')
                sessions_list.append({
                    'token': t['token'],
                    'subject': parts[0] if len(parts)>0 else '',
                    'faculty': parts[1] if len(parts)>1 else '',
                    'branch': parts[2] if len(parts)>2 else '',
                    'semester': parts[3] if len(parts)>3 else '',
                    'created_at': t.get('created_at'),
                    'expires_at': t.get('expires_at'),
                    'is_active': is_active
                })
            except:
                continue
        total_sessions = len(tokens)
        att_res = supabase.table('attendance').select('*').execute()
        att_list = att_res.data or []
        total_attendance = len(att_list)
        # Risk alerts: active sessions with no attendance
        risk_alerts = []
        for s in sessions_list:
            if s['is_active'] and not any(a.get('session_token') == s['token'] for a in att_list):
                risk_alerts.append(s)
        # AI Insights: simple attendance analysis
        counts = Counter(a.get('session_token') for a in att_list)
        ai_insights = []
        # Top session by attendance
        if counts:
            top_token, top_count = counts.most_common(1)[0]
            top_s = next((x for x in sessions_list if x['token']==top_token), None)
            if top_s:
                ai_insights.append(f"Top session by attendance: {top_s['subject']} with {top_count} attendees.")
        # Low attendance tips
        for s in sessions_list:
            cnt = counts.get(s['token'], 0)
            if s['is_active'] and cnt > 0 and cnt < 5:
                ai_insights.append(f"Session {s['subject']} has low attendance: {cnt}. Consider sending reminders.")
            if cnt == 0:
                ai_insights.append(f"No attendance yet for session {s['subject']}. Encourage students to check in.")
        google_calendar_api_key = os.getenv('GOOGLE_CALENDAR_API_KEY', '')
        return render_template('admin/dashboard.html',
                               sessions=sessions_list,
                               stats={'total_sessions': total_sessions,
                                      'active_sessions': sum(1 for s in sessions_list if s['is_active']),
                                      'total_attendance': total_attendance},
                               risk_alerts=risk_alerts,
                               ai_insights=ai_insights,
                               google_calendar_api_key=google_calendar_api_key)
    except Exception as e:
        app.logger.error(f"Dashboard error: {e}")
        # Re-raise to show full traceback in debug mode
        raise

@app.route('/admin/attendance-count', methods=['GET'], strict_slashes=False)
@login_required
def attendance_count():
    # Return total number of attendance records
    try:
        res = supabase.table('attendance').select('id').execute()
        count = len(res.data or [])
        return jsonify({'count': count})
    except Exception as e:
        app.logger.error(f"Attendance count error: {e}")
        return jsonify({'count': 0, 'error': str(e)})

@app.route('/admin/get-qr/<token>', methods=['GET'])
@login_required
def get_qr(token):
    try:
        # Fetch token record
        result = supabase.table('qr_tokens').select('*').eq('token', token).execute()
        if not result.data:
            return jsonify({'error': 'Invalid token'}), 404
        rec = result.data[0]
        # Generate QR image
        qr = segno.make(f"{request.host_url}attend/{token}", error='H')
        buf = io.BytesIO()
        qr.save(buf, kind='png', scale=10, border=4)
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        return jsonify({
            'qr': qr_b64,
            'token': token,
            'session': rec.get('session')
        })
    except Exception as e:
        print(f"Error in get_qr: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/toggle-session/<token>', methods=['POST'])
@login_required
def toggle_session(token):
    try:
        # Fetch session
        res = supabase.table('qr_tokens').select('expires_at').eq('token', token).execute()
        if not res.data:
            return jsonify({'error': 'Session not found'}), 404
        expires_at_str = res.data[0]['expires_at']
        # Parse expiry
        expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        # Toggle: if active (future expiry), deactivate by setting expiry to now; else activate for 24h
        new_expires_at = now if expires_at > now else now + timedelta(hours=24)
        # Update expiry only
        supabase.table('qr_tokens').update({
            'expires_at': new_expires_at.isoformat()
        }).eq('token', token).execute()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Toggle session error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/delete-session/<token>', methods=['POST'])
@login_required
def delete_session(token):
    try:
        # Delete the session
        supabase.table('qr_tokens').delete().eq('token', token).execute()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error deleting session: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/admin/attendance-history/<token>', methods=['GET'])
@login_required
def attendance_history(token):
    try:
        # Fetch session QR token details
        qr_res = supabase.table('qr_tokens').select('*').eq('token', token).execute()
        if not qr_res.data:
            return jsonify({'error': 'Invalid token'}), 404
        session_data = qr_res.data[0]
        # Query attendance within session timeframe
        created = session_data['created_at']
        expires = session_data['expires_at']
        att_res = supabase.table('attendance') \
            .select('*') \
            .gte('created_at', created) \
            .lte('created_at', expires) \
            .execute()
        return jsonify(att_res.data or [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/export-attendance/<token>', methods=['GET'])
@login_required
def export_attendance(token):
    # Fetch session token record
    qr_res = supabase.table('qr_tokens').select('*').eq('token', token).execute()
    if not qr_res.data:
        return render_template('error.html', message='Invalid token'), 404
    session_data = qr_res.data[0]
    created = session_data['created_at']
    expires = session_data['expires_at']
    # Query relevant attendance
    att_res = supabase.table('attendance') \
        .select('*') \
        .gte('created_at', created) \
        .lte('created_at', expires) \
        .execute()
    records = att_res.data or []
    # Generate CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['student_id','student_name','latitude','longitude','created_at'])
    for r in records:
        writer.writerow([
            r.get('student_id',''),
            r.get('student_name',''),
            r.get('latitude',''),
            r.get('longitude',''),
            r.get('created_at','')
        ])
    csv_data = output.getvalue()
    # Return as file download
    return Response(
        csv_data,
        mimetype='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=attendance_{token}.csv'
        }
    )

@app.route('/admin/generate-qr', methods=['POST'])
@login_required
def generate_qr():
    try:
        data = request.get_json()
        session_name = data.get('session')
        faculty = data.get('faculty')
        branch = data.get('branch')
        semester = data.get('semester')
        # Validate input
        if not all([session_name, faculty, branch, semester]):
            missing = [field for field in ['session','faculty','branch','semester'] if not data.get(field)]
            return jsonify({'error': f"Missing fields: {', '.join(missing)}"}), 400
        # Build session string identifier
        session_str = f"{session_name} - {faculty} - {branch} - {semester}"
        # Prevent duplicate active session
        now = datetime.now(timezone.utc)
        existing = supabase.table('qr_tokens')\
            .select('token', 'expires_at')\
            .eq('session', session_str)\
            .execute().data or []
        for rec in existing:
            try:
                exp = datetime.fromisoformat(rec['expires_at'].replace('Z', '+00:00'))
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)
                if exp > now:
                    return jsonify({'success': False, 'error': 'Session already active'}), 400
            except:
                continue
        # Check for existing active QR for this session
        existing = supabase.table('qr_tokens')\
            .select('*')\
            .eq('session', session_str)\
            .gte('expires_at', now.isoformat())\
            .execute()
        if existing.data and existing.data[0]:
            # Reuse existing token
            existing_rec = existing.data[0]
            token = existing_rec['token']
            expires = datetime.fromisoformat(existing_rec['expires_at'].replace('Z', '+00:00'))
            # Generate QR image
            qr = segno.make(f"{request.host_url}attend/{token}", error='H')
            buf = io.BytesIO()
            qr.save(buf, kind='png', scale=6, border=4)
            qr_b64 = base64.b64encode(buf.getvalue()).decode()
            return jsonify({'success': True,
                            'existing': True,
                            'qr': qr_b64,
                            'token': token,
                            'session': session_str,
                            'subject': session_name,
                            'faculty': faculty,
                            'branch': branch,
                            'semester': semester,
                            'expires_at': expires.isoformat()})
        else:
            token = secrets.token_urlsafe(32)
            expires = now + timedelta(hours=24)
            # Generate QR
            qr = segno.make(f"{request.host_url}attend/{token}", error='H')
            buf = io.BytesIO()
            qr.save(buf, kind='png', scale=6, border=4)
            qr_b64 = base64.b64encode(buf.getvalue()).decode()
            # Insert
            rec = {
                'token': token,
                'session': session_str,
                'created_at': now.isoformat(),
                'expires_at': expires.isoformat()
            }
            res = supabase.table('qr_tokens').insert(rec).execute()
            if not res.data:
                return jsonify({'error': 'Failed to create session'}), 500
            return jsonify({'success': True,
                            'qr': qr_b64,
                            'token': token,
                            'session': session_str,
                            'subject': session_name,
                            'faculty': faculty,
                            'branch': branch,
                            'semester': semester,
                            'expires_at': expires.isoformat()})
    except Exception as e:
        print("QR generation error:", e)
        return jsonify({'error': str(e)}), 500

@app.route('/admin/get-sessions', methods=['GET'])
@login_required
def get_sessions():
    try:
        res = supabase.table('qr_tokens').select('*').order('created_at', desc=True).execute()
        tokens = res.data or []
        now = datetime.now(timezone.utc)
        sessions = []
        for t in tokens:
            expires = datetime.fromisoformat(t['expires_at'].replace('Z','+00:00'))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            is_active = expires > now
            parts = t['session'].split(' - ')
            sessions.append({
                'token': t['token'],
                'subject': parts[0] if parts else '',
                'faculty': parts[1] if len(parts)>1 else '',
                'branch': parts[2] if len(parts)>2 else '',
                'semester': parts[3] if len(parts)>3 else '',
                'is_active': is_active
            })
        return jsonify({'success': True, 'sessions': sessions})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/get-active-sessions', methods=['GET'])
@login_required
def get_active_sessions():
    try:
        result = supabase.table('qr_tokens').select('*').execute()
        sessions = result.data if result.data else []
        active_sessions = [session for session in sessions if session['expires_at'] > datetime.now().isoformat()]
        return jsonify(active_sessions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return 'OK', 200

@app.route('/admin/create-session', methods=['GET', 'POST'])
@login_required
def create_session():
    """Render the Create Session page"""
    if request.method == 'POST':
        # Handle session creation and QR generation
        session_name = request.form.get('name')
        faculty = request.form.get('faculty')
        branch = request.form.get('branch')
        semester = request.form.get('semester')
        now = datetime.now(timezone.utc)
        # Build full session string
        session_str = f"{session_name} - {faculty} - {branch} - {semester}"
        # Insert new token record
        token = uuid.uuid4().hex
        expires_at = (now + timedelta(hours=24)).isoformat()
        supabase.table('qr_tokens').insert({
            'token': token,
            'session': session_str,
            'created_at': now.isoformat(),
            'expires_at': expires_at
        }).execute()
        # Generate QR b64
        qr = segno.make(f"{request.host_url}attend/{token}", error='H')
        buf = io.BytesIO()
        qr.save(buf, kind='png', scale=6, border=4)
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        return jsonify({'success': True, 'token': token, 'qr': qr_b64})
    return render_template('admin/create_session.html')

@app.route('/attend/<token>', methods=['GET', 'POST'])
def attend(token):
    try:
        # Get session details
        result = supabase.table('qr_tokens').select('*').eq('token', token).execute()
        
        if not result.data:
            return render_template('error.html', message='Invalid or expired QR code')
            
        session_data = result.data[0]
        
        # Check if expired
        expires_at = datetime.fromisoformat(session_data['expires_at'].replace('Z', '+00:00'))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return render_template('error.html', message='QR code has expired')
            
        # Extract session parts (format: "Subject - Faculty - Branch - Semester")
        session_parts = session_data['session'].split(' - ')
        subject = session_parts[0] if len(session_parts) > 0 else ''
        faculty = session_parts[1] if len(session_parts) > 1 else ''
        branch = session_parts[2] if len(session_parts) > 2 else ''
        semester = session_parts[3] if len(session_parts) > 3 else ''
        
        # Create session info for template
        session_info = {
            'token': token,
            'name': subject,  
            'faculty': faculty,
            'branch': branch,
            'semester': semester,
            'created_at': session_data.get('created_at')
        }
        
        if request.method == 'POST':
            data = request.get_json()
            student_id = data.get('student_id')
            student_name = data.get('student_name')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            photo = data.get('photo')
            
            if not all([student_id, student_name, latitude, longitude, photo]):
                return jsonify({'success': False, 'message': 'All fields are required'})
            
            # Save attendance with location and photo
            attendance_data = {
                'student_id': student_id,
                'student_name': student_name,
                'latitude': float(latitude),
                'longitude': float(longitude),
                'photo': photo,  
                'session_token': token,
                'created_at': datetime.now().isoformat()
            }
            
            result = supabase.table('attendance').insert(attendance_data).execute()
            
            if not result.data:
                return jsonify({'success': False, 'message': 'Failed to save attendance'})
            
            return jsonify({'success': True})
        
        return render_template('attendance_form.html', session=session_info)
        
    except Exception as e:
        print(f"Error: {e}")
        return render_template('error.html', message='Failed to process attendance')

@app.route('/admin/get-risk-alerts', methods=['GET'])
@login_required
def get_risk_alerts():
    try:
        # Get all tokens
        res = supabase.table('qr_tokens').select('*').execute()
        all_tokens = res.data or []
        tokens = [t for t in all_tokens if t.get('session','').split(' - ')[1:2] and t['session'].split(' - ')[1] == session.get('admin')]
        now = datetime.now(timezone.utc)
        sessions_list = []
        
        # Process sessions
        for t in tokens:
            try:
                expires = datetime.fromisoformat(t['expires_at'].replace('Z', '+00:00'))
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                is_active = expires > now
                if is_active:  # Only include active sessions
                    parts = t['session'].split(' - ')
                    sessions_list.append({
                        'token': t['token'],
                        'subject': parts[0] if len(parts)>0 else '',
                        'faculty': parts[1] if len(parts)>1 else '',
                        'branch': parts[2] if len(parts)>2 else '',
                        'semester': parts[3] if len(parts)>3 else ''
                    })
            except:
                continue
        
        # Get attendance records
        att_res = supabase.table('attendance').select('*').execute()
        all_att = att_res.data or []
        valid_tokens = {t['token'] for t in tokens}
        att_list = [a for a in all_att if a.get('session_token') in valid_tokens]
        
        # Find active sessions with no attendance
        risk_alerts = []
        for s in sessions_list:
            if not any(a.get('session_token') == s['token'] for a in att_list):
                risk_alerts.append(s)
                
        return jsonify({'success': True, 'risk_alerts': risk_alerts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/admin/get-ai-insights', methods=['GET'])
@login_required
def get_ai_insights():
    try:
        # Fetch attendance and sessions same as dashboard
        res = supabase.table('qr_tokens')\
            .select('*')\
            .order('created_at', desc=True)\
            .execute()
        tokens = res.data or []
        now = datetime.now(timezone.utc)
        sessions_list = []
        for t in tokens:
            expires = datetime.fromisoformat(t['expires_at'].replace('Z', '+00:00'))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            is_active = expires > now
            parts = t['session'].split(' - ')
            sessions_list.append({'token': t['token'], 'subject': parts[0] if parts else '' , 'is_active': is_active})
        att_res = supabase.table('attendance').select('*').execute()
        att_list = att_res.data or []
        # Compute insights
        counts = Counter(a.get('session_token') for a in att_list)
        ai_insights = []
        if counts:
            top_token, top_count = counts.most_common(1)[0]
            top_s = next((x for x in sessions_list if x['token']==top_token), None)
            if top_s:
                ai_insights.append(f"Top session by attendance: {top_s['subject']} with {top_count} attendees.")
        for s in sessions_list:
            cnt = counts.get(s['token'], 0)
            if s['is_active'] and cnt>0 and cnt<5:
                ai_insights.append(f"Session {s['subject']} has low attendance: {cnt}. Consider sending reminders.")
            if cnt==0:
                ai_insights.append(f"No attendance yet for session {s['subject']}. Encourage students to check in.")
        return jsonify({'success': True, 'ai_insights': ai_insights})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == "__main__":
    # Print all routes for debugging
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(rule)
    # Bind to localhost to allow 127.0.0.1 access
    app.run(host="127.0.0.1", port=5000, debug=True)
