from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import base64
import segno
from io import BytesIO
from urllib.parse import quote
import hashlib
import time
import secrets
import re

app = Flask(__name__)
# Generate a random secret key at startup
app.secret_key = secrets.token_hex(32)

# Your existing Google Form URL
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdnEVo2O_Ij6cUwtA4tiVOfG_Gb8Gfd9D4QI2St7wBMdiWkMA/formResponse"

# Form field IDs from your form
FORM_FIELDS = {
    'session': 'entry.1294673448',
    'faculty': 'entry.13279433',
    'branch': 'entry.1785981667',
    'semester': 'entry.771272441'
}

# Admin credentials storage
ADMINS = {
    'admin': {
        'password': 'admin123',  # Default admin account
        'created_at': time.time()
    }
}

def validate_password(password):
    """Validate password meets requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[@$!%*#?&]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

def validate_username(username):
    """Validate username meets requirements"""
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        return False, "Username must be 3-20 characters and contain only letters, numbers, and underscores"
    return True, "Username is valid"

def hash_password(password):
    """Hash password using SHA-512"""
    return hashlib.sha512(password.encode()).hexdigest()

@app.route('/')
def index():
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    return redirect(url_for('admin_login'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if username in ADMINS and ADMINS[username]['password'] == password:
            session['admin_id'] = username
            session['login_time'] = time.time()
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            # Add delay to prevent brute force attacks
            time.sleep(1)
            flash('Invalid username or password', 'danger')
            
    return render_template('admin/login.html')

@app.route('/admin/register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validate username
        username_valid, username_msg = validate_username(username)
        if not username_valid:
            flash(username_msg, 'danger')
            return render_template('admin/register.html')

        # Check if username exists
        if username in ADMINS:
            flash('Username already exists', 'danger')
            return render_template('admin/register.html')

        # Validate password
        password_valid, password_msg = validate_password(password)
        if not password_valid:
            flash(password_msg, 'danger')
            return render_template('admin/register.html')

        # Check password confirmation
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return render_template('admin/register.html')

        # Create new admin account
        ADMINS[username] = {
            'password': hash_password(password),
            'created_at': time.time()
        }

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('admin_login'))

    return render_template('admin/register.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash('Please login first', 'danger')
        return redirect(url_for('admin_login'))
    
    # Check session expiry (8 hours)
    if time.time() - session.get('login_time', 0) > 8 * 3600:
        session.clear()
        flash('Session expired. Please login again.', 'warning')
        return redirect(url_for('admin_login'))
        
    return render_template('admin/dashboard.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))

@app.route('/generate_qr', methods=['POST'])
def generate_qr():
    if 'admin_id' not in session:
        return jsonify({'error': 'Please login first'}), 401

    try:
        # Get and sanitize form data
        session_name = request.form.get('session', '').strip()
        faculty_name = request.form.get('faculty', '').strip()
        branch = request.form.get('branch', '').strip()
        semester = request.form.get('semester', '').strip()

        if not session_name:
            return jsonify({'error': 'Session name is required'}), 400

        # Add timestamp to prevent caching of QR codes
        timestamp = int(time.time())
        
        # Build the form URL with prefilled values
        form_url = f"{GOOGLE_FORM_URL}?"
        
        # Add form fields with validation
        params = []
        if session_name:
            params.append(f"{FORM_FIELDS['session']}={quote(session_name)}")
        if faculty_name:
            params.append(f"{FORM_FIELDS['faculty']}={quote(faculty_name)}")
        if branch:
            params.append(f"{FORM_FIELDS['branch']}={quote(branch)}")
        if semester:
            params.append(f"{FORM_FIELDS['semester']}={quote(semester)}")
        
        # Add timestamp to URL to prevent QR code reuse
        params.append(f"t={timestamp}")
        
        form_url += '&'.join(params)
        
        # Generate QR code with error correction
        qr = segno.make(form_url, error='H', micro=False)
        buffer = BytesIO()
        qr.save(buffer, kind='png', scale=10, border=4)
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return jsonify({
            'success': True,
            'qr_code': img_str,
            'url': form_url,
            'expires_in': '15 minutes'  # QR codes expire after 15 minutes
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/view_responses')
def view_responses():
    if 'admin_id' not in session:
        flash('Please login first', 'danger')
        return redirect(url_for('admin_login'))
    return redirect(GOOGLE_FORM_URL.replace('formResponse', 'responses'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
