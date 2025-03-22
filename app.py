import os
import segno
import logging
from io import BytesIO
import base64
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', '5e7f9b7c1a4d3e2b8f6c9a0d5e2f1b4a7890123456789abcdef0123456789ab')

# Supabase configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://aaluawvcohqfhevkdnuv.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhbHVhd3Zjb2hxZmhldmtkbnV2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNzY3MzcsImV4cCI6MjA1Nzg1MjczN30.kKL_B4sw1nwY6lbzgyPHQYoC_uqDsPkT51ZOnhr6MNA')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        
        try:
            result = supabase.table('admins').select('*').eq('username', username).execute()
            if result.data and check_password_hash(result.data[0]['password_hash'], password):
                session['admin_id'] = result.data[0]['id']
                session['username'] = username
                flash('Login successful!', 'success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid username or password', 'danger')
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash('An error occurred during login', 'danger')
            
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash('Please login first', 'danger')
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    if 'admin_id' not in session:
        return jsonify({'error': 'Please login first'}), 401

    try:
        session_name = request.form.get('session')
        if not session_name:
            return jsonify({'error': 'Session name is required'}), 400

        logger.info(f"Generating QR code for session: {session_name}")

        # Generate unique token and expiry time
        token = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8')
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        # Save token to database
        try:
            logger.info("Saving token to database")
            result = supabase.table('qr_tokens').insert({
                'token': token,
                'session': session_name,
                'expires_at': expires_at.isoformat()
            }).execute()
            
            if not result.data:
                logger.error("Failed to save token to database")
                return jsonify({'error': 'Failed to save token to database'}), 500

            logger.info("Token saved successfully")
                
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return jsonify({'error': 'Failed to save token to database'}), 500

        # Generate QR code
        try:
            logger.info("Generating QR code image")
            
            # Use the full URL for QR code
            base_url = request.host_url.rstrip('/')
            if base_url.startswith('http://'):
                base_url = base_url.replace('http://', 'https://')
            attendance_url = f"{base_url}/mark_attendance/{token}"

            # Generate QR code using segno
            qr = segno.make(attendance_url, micro=False)
            buffer = BytesIO()
            qr.save(buffer, kind='png', scale=10, border=4)
            buffer.seek(0)
            img_str = base64.b64encode(buffer.getvalue()).decode()

            logger.info("QR code generated successfully")
            response_data = {
                'success': True,
                'qr_code': img_str,
                'url': attendance_url,
                'expires_at': expires_at.isoformat()
            }
            logger.info("Sending response with QR code")
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"QR generation error: {str(e)}")
            return jsonify({
                'error': 'Failed to generate QR code image',
                'details': str(e)
            }), 500

    except Exception as e:
        logger.error(f"General error in generate_qr: {str(e)}")
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/mark_attendance/<token>', methods=['GET', 'POST'])
def mark_attendance(token):
    try:
        # Verify token
        result = supabase.table('qr_tokens').select('*').eq('token', token).execute()
        if not result.data:
            return render_template('error.html', message='Invalid or expired QR code')

        token_data = result.data[0]
        if datetime.fromisoformat(token_data['expires_at']) < datetime.utcnow():
            return render_template('error.html', message='QR code has expired')

        if request.method == 'POST':
            student_id = request.form.get('student_id')
            if not student_id:
                return render_template('error.html', message='Student ID is required')

            # Mark attendance
            try:
                result = supabase.table('attendance').insert({
                    'student_id': student_id,
                    'status': 'present'
                }).execute()
                
                if not result.data:
                    raise Exception("Failed to mark attendance")
                    
                return render_template('success.html', message='Attendance marked successfully!')
            except Exception as e:
                logger.error(f"Attendance marking error: {str(e)}")
                return render_template('error.html', message='Failed to mark attendance')

        return render_template('attendance_form.html', token=token)

    except Exception as e:
        logger.error(f"Error in mark_attendance: {str(e)}")
        return render_template('error.html', message='An error occurred')

@app.route('/admin/attendance')
def admin_attendance():
    if 'admin_id' not in session:
        return jsonify({'error': 'Please login first'}), 401

    try:
        result = supabase.table('attendance').select('*').order('created_at', desc=True).limit(10).execute()
        return jsonify(result.data if result.data else [])
    except Exception as e:
        logger.error(f"Error fetching attendance: {str(e)}")
        return jsonify({'error': 'Failed to fetch attendance records'}), 500

@app.route('/register_admin', methods=['GET', 'POST'])
def register_admin():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not username or not password or not confirm_password:
            flash('All fields are required', 'danger')
            return redirect(url_for('register_admin'))
            
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register_admin'))
            
        try:
            # Check if username already exists
            result = supabase.table('admins').select('*').eq('username', username).execute()
            if result.data:
                flash('Username already exists', 'danger')
                return redirect(url_for('register_admin'))
                
            # Hash password and create new admin
            password_hash = generate_password_hash(password)
            result = supabase.table('admins').insert({
                'username': username,
                'password_hash': password_hash
            }).execute()
            
            if not result.data:
                raise Exception("Failed to create admin account")
                
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('admin_login'))
            
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            flash('An error occurred during registration', 'danger')
            return redirect(url_for('register_admin'))
        
    return render_template('register_admin.html')

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
