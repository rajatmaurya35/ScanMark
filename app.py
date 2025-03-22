import os
import json
import secrets
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, send_file, make_response, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client
from functools import wraps
import qrcode
from io import BytesIO
import base64
import logging

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'dev_5e7f9b7c1a4d3e2b8f6c9a0d5e2f1b4a')

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase_url = "https://aaluawvcohqfhevkdnuv.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhbHVhd3Zjb2hxZmhldmtkbnV2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNzY3MzcsImV4cCI6MjA1Nzg1MjczN30.kKL_B4sw1nwY6lbzgyPHQYoC_uqDsPkT51ZOnhr6MNA"
supabase = create_client(supabase_url, supabase_key)

# Create static directory for QR codes
os.makedirs('static/qr_codes', exist_ok=True)

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            flash('Please log in first', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Error handlers
@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server error: {str(error)}")
    return render_template('error.html', message="Internal server error. Please try again later."), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', message="Page not found."), 404

# Initialize database tables if they don't exist
@app.before_first_request
def init_db():
    try:
        # Check if tables exist by querying them
        tables = ['admins', 'attendance', 'qr_tokens']
        for table in tables:
            try:
                supabase.table(table).select('*').limit(1).execute()
            except Exception as e:
                logger.error(f"Table {table} not found: {str(e)}")
                return jsonify({'error': f'Database table {table} not found'}), 500
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        return jsonify({'error': 'Failed to initialize database'}), 500

# Get the public URL for the application
def get_public_url():
    """Get the public URL for the application"""
    if os.getenv('VERCEL_URL'):
        return f"https://{os.getenv('VERCEL_URL')}"
    return request.url_root.rstrip('/')

@app.route('/')
def index():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not all([username, password]):
            flash('Please provide both username and password', 'danger')
            return redirect(url_for('admin_login'))
            
        try:
            result = supabase.table('admins').select('*').eq('username', username).execute()
            if result.data and len(result.data) > 0:
                admin = result.data[0]
                if check_password_hash(admin['password_hash'], password):
                    session['admin_id'] = admin['id']
                    flash('Login successful!', 'success')
                    return redirect(url_for('admin_dashboard'))
                    
            flash('Invalid username or password', 'danger')
            return redirect(url_for('admin_login'))
            
        except Exception as e:
            logger.error(f"Error during admin login: {str(e)}")
            flash('An error occurred during login', 'danger')
            return redirect(url_for('admin_login'))
            
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/admin/attendance')
@admin_required
def get_attendance():
    try:
        # Get recent attendance records
        result = supabase.table('attendance').select('*').order('created_at', desc=True).limit(50).execute()
        
        if not result.data:
            return jsonify([])

        return jsonify(result.data)
        
    except Exception as e:
        logger.error(f"Error fetching attendance: {str(e)}")
        return jsonify({'error': 'Failed to fetch attendance records'}), 500

@app.route('/generate_qr', methods=['POST'])
@admin_required
def generate_qr():
    try:
        # Generate a random token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(minutes=15)
        
        # Save token to database
        token_data = {
            'token': token,
            'session': 'attendance',
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at.isoformat()
        }
        
        result = supabase.table('qr_tokens').insert(token_data).execute()
        
        if not result.data:
            logger.error("Failed to save QR token to database")
            return jsonify({'error': 'Failed to generate QR code'}), 500

        # Generate QR code
        attendance_url = f"{get_public_url()}/attendance/{token}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(attendance_url)
        qr.make(fit=True)
        
        # Create QR code image
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        
        return jsonify({
            'qr_code': f"data:image/png;base64,{img_str}",
            'expires_at': expires_at.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating QR code: {str(e)}")
        return jsonify({'error': 'Failed to generate QR code'}), 500

@app.route('/attendance/<token>', methods=['GET', 'POST'])
def mark_attendance(token):
    try:
        # Verify token
        result = supabase.table('qr_tokens').select('*').eq('token', token).execute()
        if not result.data:
            flash('Invalid or expired QR code', 'danger')
            return render_template('error.html', message='Invalid or expired QR code')
            
        token_data = result.data[0]
        if datetime.fromisoformat(token_data['expires_at']) < datetime.now(timezone.utc):
            flash('QR code has expired', 'danger')
            return render_template('error.html', message='QR code has expired')
            
        if request.method == 'POST':
            student_id = request.form.get('student_id')
            
            if not student_id:
                flash('Please provide your student ID', 'danger')
                return redirect(url_for('mark_attendance', token=token))
                
            try:
                # Record attendance
                attendance_data = {
                    'student_id': student_id,
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'status': 'present'
                }
                
                result = supabase.table('attendance').insert(attendance_data).execute()
                if result.data:
                    flash('Attendance marked successfully!', 'success')
                    return render_template('success.html', message='Attendance marked successfully!')
                else:
                    flash('Failed to mark attendance', 'danger')
                    return redirect(url_for('mark_attendance', token=token))
                    
            except Exception as e:
                logger.error(f"Error marking attendance: {str(e)}")
                flash('An error occurred while marking attendance', 'danger')
                return redirect(url_for('mark_attendance', token=token))
                
        return render_template('attendance_form.html', token=token)
        
    except Exception as e:
        logger.error(f"Error processing attendance: {str(e)}")
        flash('An error occurred', 'danger')
        return render_template('error.html', message='An error occurred')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
