import os
import qrcode
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
app.secret_key = '5e7f9b7c1a4d3e2b8f6c9a0d5e2f1b4a7890123456789abcdef0123456789ab'

# Supabase configuration
SUPABASE_URL = "https://aaluawvcohqfhevkdnuv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhbHVhd3Zjb2hxZmhldmtkbnV2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNzY3MzcsImV4cCI6MjA1Nzg1MjczN30.kKL_B4sw1nwY6lbzgyPHQYoC_uqDsPkT51ZOnhr6MNA"
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
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        session_name = request.form.get('session')
        if not session_name:
            return jsonify({'error': 'Session name is required'}), 400

        # Generate unique token
        token = base64.urlsafe_b64encode(os.urandom(16)).decode('utf-8')

        # Save token to database
        try:
            supabase.table('qr_tokens').insert({
                'token': token,
                'session': session_name,
                'expires_at': datetime.utcnow() + timedelta(minutes=15)
            }).execute()
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return jsonify({'error': 'Failed to save token'}), 500

        # Generate QR code
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            attendance_url = f"{request.host_url}mark_attendance/{token}"
            qr.add_data(attendance_url)
            qr.make(fit=True)

            # Create QR code image
            img_buffer = BytesIO()
            img = qr.make_image(fill_color="black", back_color="white")
            img.save(img_buffer, format='PNG')
            img_str = base64.b64encode(img_buffer.getvalue()).decode()

            return jsonify({
                'qr_code': img_str,
                'url': attendance_url
            })
        except Exception as e:
            logger.error(f"QR generation error: {str(e)}")
            return jsonify({'error': 'Failed to generate QR image'}), 500

    except Exception as e:
        logger.error(f"General error: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@app.route('/admin/attendance')
def admin_attendance():
    if 'admin_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        result = supabase.table('attendance').select('*').order('created_at.desc').limit(10).execute()
        return jsonify(result.data)
    except Exception as e:
        logger.error(f"Error fetching attendance: {str(e)}")
        return jsonify({'error': 'Failed to fetch attendance'}), 500

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
            supabase.table('attendance').insert({
                'student_id': student_id,
                'status': 'present'
            }).execute()

            return render_template('success.html')

        return render_template('attendance_form.html', token=token)

    except Exception as e:
        logger.error(f"Error marking attendance: {str(e)}")
        return render_template('error.html', message='An error occurred')

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
            
        # Check if username already exists
        result = supabase.table('admins').select('*').eq('username', username).execute()
        if result.data:
            flash('Username already exists', 'danger')
            return redirect(url_for('register_admin'))
            
        # Hash password and create new admin
        password_hash = generate_password_hash(password)
        supabase.table('admins').insert({
            'username': username,
            'password_hash': password_hash
        }).execute()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('admin_login'))
        
    return render_template('register_admin.html')

@app.route('/logout')
def logout():
    session.clear()
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
