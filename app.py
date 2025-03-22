import os
import json
import secrets
from datetime import datetime, timedelta
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
app.config['SECRET_KEY'] = '5e7f9b7c1a4d3e2b8f6c9a0d5e2f1b4a7890123456789abcdef0123456789ab'

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase_url = "https://aaluawvcohqfhevkdnuv.supabase.co"
supabase_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhbHVhd3Zjb2hxZmhldmtkbnV2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNzY3MzcsImV4cCI6MjA1Nzg1MjczN30.kKL_B4sw1nwY6lbzgyPHQYoC_uqDsPkT51ZOnhr6MNA"
supabase = create_client(supabase_url, supabase_key)

# Create static directory for QR codes if it doesn't exist
os.makedirs('static/qr_codes', exist_ok=True)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_id'):
            flash('Please log in first', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    if session.get('admin_id'):
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password', 'danger')
            return redirect(url_for('admin_login'))
            
        try:
            result = supabase.table('admins').select('*').eq('username', username).execute()
            
            if result.data and len(result.data) > 0:
                admin = result.data[0]
                if check_password_hash(admin['password_hash'], password):
                    session['admin_id'] = admin['id']
                    session['username'] = admin['username']
                    flash('Login successful!', 'success')
                    return redirect(url_for('admin_dashboard'))
            
            flash('Invalid username or password', 'danger')
            return redirect(url_for('admin_login'))
            
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            flash('An error occurred', 'danger')
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
        result = supabase.table('attendance').select('*').order('created_at', desc=True).limit(50).execute()
        return jsonify(result.data if result.data else [])
    except Exception as e:
        logger.error(f"Error fetching attendance: {str(e)}")
        return jsonify({'error': 'Failed to fetch records'}), 500

@app.route('/generate_qr', methods=['POST'])
@admin_required
def generate_qr():
    try:
        token = secrets.token_urlsafe(32)
        session_name = request.form.get('session', 'Default Session')
        expires_at = datetime.utcnow() + timedelta(minutes=15)
        
        token_data = {
            'token': token,
            'session': session_name,
            'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        result = supabase.table('qr_tokens').insert(token_data).execute()
        
        if not result.data:
            raise Exception("Failed to save token")
            
        attendance_url = f"{request.host_url.rstrip('/')}/attendance/{token}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(attendance_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = BytesIO()
        img.save(img_buffer, format='PNG')
        img_str = base64.b64encode(img_buffer.getvalue()).decode()
        
        return jsonify({
            'qr_code': img_str,
            'url': attendance_url,
            'expires_at': expires_at.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"Error generating QR: {str(e)}")
        return jsonify({'error': 'Failed to generate QR'}), 500

@app.route('/attendance/<token>', methods=['GET', 'POST'])
def mark_attendance(token):
    try:
        result = supabase.table('qr_tokens').select('*').eq('token', token).execute()
        
        if not result.data:
            flash('Invalid QR code', 'danger')
            return render_template('error.html', message='Invalid QR code')
            
        token_data = result.data[0]
        expires_at = datetime.strptime(token_data['expires_at'], '%Y-%m-%d %H:%M:%S')
        
        if expires_at < datetime.utcnow():
            flash('QR code has expired', 'danger')
            return render_template('error.html', message='QR code has expired')
            
        if request.method == 'POST':
            student_id = request.form.get('student_id')
            
            if not student_id:
                flash('Please provide your student ID', 'danger')
                return redirect(url_for('mark_attendance', token=token))
                
            attendance_data = {
                'student_id': student_id,
                'status': 'present'
            }
            
            result = supabase.table('attendance').insert(attendance_data).execute()
            
            if result.data:
                flash('Attendance marked successfully!', 'success')
                return render_template('success.html')
            else:
                flash('Failed to mark attendance', 'danger')
                return redirect(url_for('mark_attendance', token=token))
                
        return render_template('attendance_form.html', token=token)
        
    except Exception as e:
        logger.error(f"Error marking attendance: {str(e)}")
        return render_template('error.html', message='An error occurred')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))

@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Server error: {str(error)}")
    return render_template('error.html', message="Internal server error"), 500

if __name__ == '__main__':
    app.run(debug=True)
