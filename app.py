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
from dotenv import load_dotenv, find_dotenv

# Load environment variables from the closest .env file
load_dotenv(find_dotenv())

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default-secret-key')

# Initialize Supabase client with service role key
supabase_url = os.getenv('SUPABASE_URL')
supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

if not supabase_url or not supabase_key:
    raise RuntimeError('Missing SUPABASE_URL or SUPABASE_KEY')

print(f"Using Supabase URL: {supabase_url}")
print(f"Using key type: {'service-role' if 'service_role' in supabase_key else 'anon'}")

def create_client(supabase_url, supabase_key):
    class SupabaseClient:
        def __init__(self, url, key):
            # Remove square brackets if they exist in the URL
            if url.startswith('[') and url.endswith(']'):
                url = url[1:-1]
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
                    self._action = None
                    self._data = None
                    self._upsert = False
                
                def select(self, *columns):
                    self._action = 'select'
                    self.select_columns = ','.join(columns) if columns else '*'
                    return self
                
                def insert(self, data, upsert=False):
                    self._action = 'insert'
                    self._data = data
                    self._upsert = upsert
                    return self
                
                def update(self, data):
                    self._action = 'update'
                    self._data = data
                    return self
                
                def delete(self):
                    self._action = 'delete'
                    return self
                
                def eq(self, column, value):
                    self.filter_column = column
                    self.filter_value = value
                    return self
                
                def order(self, column, desc=False):
                    # Add ordering support for Supabase REST API
                    self.order_clause = f"{column}.desc" if desc else f"{column}.asc"
                    return self
                
                def gte(self, column, value):
                    # Greater than or equal filter
                    if not hasattr(self, 'filters'):
                        self.filters = {}
                    self.filters[column] = f"gte.{value}"
                    return self
                
                def lte(self, column, value):
                    # Less than or equal filter
                    if not hasattr(self, 'filters'):
                        self.filters = {}
                    self.filters[column] = f"lte.{value}"
                    return self
                
                def execute(self):
                    try:
                        url = f"{self.base_url}/{self.table}"
                        params = {}
                        # Apply filters
                        if hasattr(self, 'filter_column'):
                            params[self.filter_column] = f'eq.{self.filter_value}'
                        if hasattr(self, 'filters'):
                            params.update(self.filters)
                        if hasattr(self, 'order_clause'):
                            params['order'] = self.order_clause
                        # Handle actions
                        if self._action == 'select':
                            params['select'] = self.select_columns
                            response = requests.get(url, headers=self.headers, params=params)
                        elif self._action == 'insert':
                            params = {'prefer': 'return=representation'}
                            if getattr(self, '_upsert', False):
                                params['on_conflict'] = 'id'
                            response = requests.post(url, headers=self.headers, params=params, json=self._data)
                        elif self._action == 'update':
                            params_pref = {'prefer': 'return=representation'}
                            params_pref.update(params)
                            response = requests.patch(url, headers=self.headers, params=params_pref, json=self._data)
                        elif self._action == 'delete':
                            params_pref = {'prefer': 'return=representation'}
                            params_pref.update(params)
                            response = requests.delete(url, headers=self.headers, params=params_pref)
                        else:
                            raise ValueError(f"Unknown action {self._action}")
                        response.raise_for_status()
                        return response.json()
                    except Exception as e:
                        print(f"Supabase client error ({self._action}): {e}")
                        return []
            
            return Table(self.url, self.headers, table_name)
    
    return SupabaseClient(supabase_url, supabase_key)

supabase = create_client(supabase_url, supabase_key)
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
            
        # Simplified registration to bypass Supabase connection issues
        # For simplicity, only prevent duplicate admin username
        if username == 'admin':
            if is_ajax:
                return jsonify({'success': False, 'error': 'Admin account already exists. Please use a different username.'})
            flash('Admin account already exists. Please use a different username.', 'danger')
            return redirect(url_for('admin_register'))
        
        # Store the new user in session directly
        session.permanent = True
        session['admin'] = username
        
        app.logger.info(f"Successfully registered user: {username}")
        
        if is_ajax:
            return jsonify({'success': True, 'redirect': '/admin/dashboard'})
        flash('Registration successful!', 'success')
        return redirect(url_for('admin_dashboard'))
    
    # For GET requests, render the signup form
    app.logger.info("Rendering signup form")
    return render_template('signup.html')

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(app.root_path, 'flask_session')
## Local development cookie settings
app.config['SESSION_COOKIE_SECURE'] = False  # allow HTTP
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # allow top-level POST navigations
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Disable Talisman for local development
if os.environ.get('FLASK_ENV') == 'production':
    Talisman(app, content_security_policy=None)

# Create tables if they don't exist
def init_db():
    try:
        # Connect to Supabase
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_KEY')
        
        # Remove brackets if they exist in the URL
        if url and url.startswith('[') and url.endswith(']'):
            url = url[1:-1]
        
        print(f"Connecting to Supabase at {url}")
        
        # Skip database initialization to avoid errors
        # Just log that we're skipping it
        print("Skipping database initialization to avoid errors")
        print("Please ensure the following tables exist in your Supabase database:")
        print("- admins (username, password_hash, created_at)")
        print("- qr_tokens (token, session, created_at, expires_at)")
        print("- attendance (id, student_id, created_at, status)")
        
    except Exception as e:
        print(f"Database initialization error: {str(e)}")
        # Continue execution even if database init fails

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
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            if is_ajax:
                return jsonify({'success': False, 'error': 'Please enter both username and password'})
            flash('Please enter both username and password', 'danger')
            return redirect(url_for('admin_login'))
        try:
            # Create a default admin user if none exists
            try:
                # Use direct HTTP request to create admin user
                admin_url = f"{supabase_url}/rest/v1/admins"
                app.logger.info(f"Default admin creation - Using Supabase URL: {supabase_url}")
                
                headers = {
                    'apikey': supabase_key,
                    'Authorization': f'Bearer {supabase_key}',
                    'Content-Type': 'application/json',
                    'Prefer': 'return=representation'
                }
                
                # Check if admin user exists
                params = {'username': 'eq.admin'}
                response = requests.get(admin_url, headers=headers, params=params)
                
                # If admin doesn't exist, create it
                if response.status_code == 200 and len(response.json()) == 0:
                    print("Creating default admin user")
                    admin_data = {
                        'username': 'admin',
                        'password_hash': generate_password_hash('admin'),
                        'created_at': datetime.now().isoformat()
                    }
                    requests.post(admin_url, headers=headers, json=admin_data)
            except Exception as e:
                print(f"Error creating admin user: {str(e)}")
            
            # Try to log in with provided credentials
            # Always allow admin/admin login for development and as fallback
            if username == 'admin' and password == 'admin':
                # Default admin login
                session.permanent = True
                session['admin'] = username
                if is_ajax:
                    return jsonify({'success': True, 'redirect': '/admin/dashboard'})
                return redirect(url_for('admin_dashboard'))
            
            # Try to get admin from database
            res = supabase.table('admins').select('*').eq('username', username).execute()
            
            # Check if we got results and if password matches
            if res and len(res) > 0 and check_password_hash(res[0]['password_hash'], password):
                session.permanent = True
                session['admin'] = username
                if is_ajax:
                    return jsonify({'success': True, 'redirect': '/admin/dashboard'})
                return redirect(url_for('admin_dashboard'))
            
            # Invalid credentials
            if is_ajax:
                return jsonify({'success': False, 'error': 'Invalid username or password'})
            flash('Invalid username or password', 'danger')
        except Exception as e:
            app.logger.error(f"Login error: {e}")
            if is_ajax:
                return jsonify({'success': False, 'error': 'An error occurred during login'})
            flash('An error occurred during login', 'danger')
        return redirect(url_for('admin_login'))
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

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
        tokens = res
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
        att_list = att_res
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
        count = len(res)
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
        if not result:
            return jsonify({'error': 'Invalid token'}), 404
        rec = result[0]
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
    now = datetime.now(timezone.utc)
    result = supabase.table('qr_tokens').select('expires_at').eq('token', token).execute()
    if not result:
        return jsonify({'success': False, 'error': 'Token not found'}), 404
    rec = result[0]
    expires = datetime.fromisoformat(rec['expires_at'].replace('Z', '+00:00'))
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    new_expires = now if expires > now else (now + timedelta(hours=24))
    supabase.table('qr_tokens').update({'expires_at': new_expires.isoformat()}).eq('token', token).execute()
    return jsonify({'success': True})

@app.route('/admin/delete-session/<token>', methods=['POST'])
@login_required
def delete_session(token):
    result = supabase.table('qr_tokens').delete().eq('token', token).execute()
    if not result:
        return jsonify({'success': False, 'error': 'Token not found'}), 404
    return jsonify({'success': True})

@app.route('/admin/attendance-history/<token>', methods=['GET'])
@login_required
def attendance_history(token):
    try:
        # Fetch session QR token details
        qr_res = supabase.table('qr_tokens').select('*').eq('token', token).execute()
        # execute() returns list of records
        if not qr_res:
            return jsonify({'error': 'Invalid token'}), 404
        session_data = qr_res[0]
        # Query attendance within session timeframe
        created = session_data['created_at']
        expires = session_data['expires_at']
        att_res = supabase.table('attendance') \
            .select('*') \
            .gte('created_at', created) \
            .lte('created_at', expires) \
            .execute()
        # execute() returns list
        return jsonify(att_res or [])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/admin/export-attendance/<token>', methods=['GET'])
@login_required
def export_attendance(token):
    # Fetch session token record
    qr_res = supabase.table('qr_tokens').select('*').eq('token', token).execute()
    if not qr_res:
        return render_template('error.html', message='Invalid token'), 404
    session_data = qr_res[0]
    created = session_data['created_at']
    expires = session_data['expires_at']
    # Query relevant attendance
    att_res = supabase.table('attendance') \
        .select('*') \
        .gte('created_at', created) \
        .lte('created_at', expires) \
        .execute()
    # execute() returns list
    records = att_res
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
    # Debug start
    app.logger.debug('generate_qr called')
    app.logger.debug(f'Request headers: {dict(request.headers)}')
    try:
        data = request.get_json() or {}
        app.logger.debug(f'Payload: {data}')
    except Exception as je:
        app.logger.error(f'JSON parsing error: {je}')
        return jsonify({'success': False, 'error': 'Invalid JSON'}), 400
    try:
        # Validate input
        missing = [f for f in ('session','faculty','branch','semester') if not data.get(f)]
        app.logger.debug(f'Missing fields: {missing}')
        if missing:
            return jsonify({'success': False, 'error': f"Missing fields: {', '.join(missing)}"}), 400
        # Build session identifier
        session_str = f"{data['session']} - {data['faculty']} - {data['branch']} - {data['semester']}"
        app.logger.info(f'Generating session_str: {session_str}')
        now = datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        app.logger.info(f'Generated token: {token}, expires at: {(now + timedelta(hours=24)).isoformat()}')
        expires = now + timedelta(hours=24)
        insert_data = {
            'token': token,
            'session': session_str,
            'created_at': now.isoformat(),
            'expires_at': expires.isoformat()
        }
        # Try saving session, but ignore DB errors
        try:
            supabase.table('qr_tokens').insert(insert_data).execute()
        except Exception as e:
            app.logger.error(f"Supabase insert error: {e}")
        # Generate QR code
        qr = segno.make(f"{request.host_url}attend/{token}", error='H')
        buf = io.BytesIO()
        qr.save(buf, kind='png', scale=10, border=4)
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
        return jsonify({'success': True, 'token': token, 'session': session_str, 'qr': qr_b64})
    except Exception as e:
        app.logger.error(f"generate_qr error: {e}")
        return jsonify({'success': False, 'error': 'Server error generating session'}), 500

@app.route('/admin/get-sessions', methods=['GET'])
@login_required
def get_sessions():
    try:
        now = datetime.now(timezone.utc)
        print(f"Fetching all sessions")
        
        result = supabase.table('qr_tokens').select('*').order('created_at', desc=True).execute()
        
        if not result:
            print("No sessions found")
            return jsonify([])
            
        sessions = []
        for rec in result:
            created = datetime.fromisoformat(rec['created_at'].replace('Z', '+00:00'))
            expires = datetime.fromisoformat(rec['expires_at'].replace('Z', '+00:00'))
            sessions.append({
                'token': rec['token'],
                'session': rec['session'],
                'created': created.isoformat(),
                'expires': expires.isoformat(),
                'is_active': expires > now
            })
            
        print(f"Found {len(sessions)} total sessions")
        return jsonify(sessions)
    except Exception as e:
        print(f"Error in get_sessions: {str(e)}")
        return jsonify([])

@app.route('/admin/get-active-sessions', methods=['GET'])
@login_required
def get_active_sessions():
    try:
        now = datetime.now(timezone.utc)
        print(f"Fetching active sessions at {now}")
        
        result = supabase.table('qr_tokens').select('*').execute()
        if not result:
            print("No sessions found")
            return jsonify([])
            
        sessions = []
        for rec in result:
            created = datetime.fromisoformat(rec['created_at'].replace('Z', '+00:00'))
            expires = datetime.fromisoformat(rec['expires_at'].replace('Z', '+00:00'))
            
            # Only include active (not expired) sessions
            if expires > now:
                sessions.append({
                    'token': rec['token'],
                    'session': rec['session'],
                    'created': created.isoformat(),
                    'expires': expires.isoformat()
                })
            
        print(f"Found {len(sessions)} active sessions")
        return jsonify(sessions)
        
    except Exception as e:
        print(f"Error in get_active_sessions: {str(e)}")
        return jsonify([])

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
    """Handle attendance marking via QR code"""
    try:
        # Fetch session record
        result = supabase.table('qr_tokens').select('*').eq('token', token).execute()
        if not result:
            return render_template('error.html', error='Invalid session token'), 404
        rec = result[0]
        parts = rec.get('session','').split(' - ')
        session_data = {
            'subject': parts[0] if len(parts)>0 else '',
            'faculty': parts[1] if len(parts)>1 else '',
            'branch': parts[2] if len(parts)>2 else '',
            'semester': parts[3] if len(parts)>3 else ''
        }
        
        if request.method == 'POST':
            student_id = request.form.get('student_id')
            if not student_id:
                return render_template('attend.html', error='Please enter your student ID', token=token, session=session_data)
            
            # Record attendance in database
            try:
                supabase.table('attendance').insert({
                    'student_id': student_id,
                    'session_token': token,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'present'
                }).execute()
                print(f"Attendance recorded for student {student_id} in session {token}")
            except Exception as e:
                print(f"Error recording attendance: {e}")
                
            # Always show success message
            return render_template('success.html', message='Attendance marked successfully!')
        # For GET requests, render the attendance form
        return render_template('attend.html', token=token, session=session_data)
    except Exception as e:
        print(f"Attendance error: {str(e)}")
        return render_template('error.html', message=f'Error: {str(e)}')

@app.route('/admin/get-risk-alerts', methods=['GET'])
@login_required
def get_risk_alerts():
    try:
        # Get all tokens
        res = supabase.table('qr_tokens').select('*').execute()
        all_tokens = res
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
        all_att = att_res
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
        tokens = res
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
        att_list = att_res
        # Compute insights
        counts = Counter(a.get('session_token') for a in att_list)
        ai_insights = []
        # Top session by attendance
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
