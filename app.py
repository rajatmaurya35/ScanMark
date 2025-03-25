import os
import base64
import segno
import logging
from io import BytesIO
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash
from urllib.parse import quote

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', '5e7f9b7c1a4d3e2b8f6c9a0d5e2f1b4a7890123456789abcdef0123456789ab')

# Google Form URL for attendance
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSdnEVo2O_Ij6cUwtA4tiVOfG_Gb8Gfd9D4QI2St7wBMdiWkMA/viewform"

# Form field IDs from the Google Form
FORM_FIELDS = {
    'name': 'entry.303339851',  # Name field
    'student_id': 'entry.451434900',  # Student ID field
    'branch': 'entry.1785981667',  # Branch field
    'semester': 'entry.771272441',  # Semester field
    'session': 'entry.1294673448',  # Session name field
    'faculty': 'entry.13279433'  # Faculty name field
}

# Admin credentials (in production, use environment variables)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')

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
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_id'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash('Please login first', 'danger')
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
        session_name = request.form.get('session')
        faculty_name = request.form.get('faculty', '')
        branch = request.form.get('branch', '')
        semester = request.form.get('semester', '')

        if not session_name:
            return jsonify({'error': 'Session name is required'}), 400

        logger.info(f"Generating QR code for session: {session_name}")

        # URL encode the parameters to handle special characters
        encoded_session = quote(session_name)
        encoded_faculty = quote(faculty_name)
        encoded_branch = quote(branch)
        encoded_semester = quote(semester)

        # Create pre-filled Google Form URL with session name and faculty
        form_url = (
            f"{GOOGLE_FORM_URL}?usp=pp_url"
            f"&{FORM_FIELDS['session']}={encoded_session}"
            f"&{FORM_FIELDS['faculty']}={encoded_faculty}"
            f"&{FORM_FIELDS['branch']}={encoded_branch}"
            f"&{FORM_FIELDS['semester']}={encoded_semester}"
        )
        
        # Generate QR code with error correction level Q (25%) for better scanning
        try:
            logger.info("Generating QR code image")
            qr = segno.make(form_url, error='Q', micro=False)
            buffer = BytesIO()
            qr.save(buffer, kind='png', scale=10, border=4)
            buffer.seek(0)
            img_str = base64.b64encode(buffer.getvalue()).decode()

            logger.info("QR code generated successfully")
            response_data = {
                'success': True,
                'qr_code': img_str,
                'url': form_url
            }
            return jsonify(response_data)

        except Exception as e:
            logger.error(f"QR generation error: {str(e)}")
            return jsonify({
                'error': 'Failed to generate QR code',
                'details': str(e)
            }), 500

    except Exception as e:
        logger.error(f"General error in generate_qr: {str(e)}")
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/view_responses')
def view_responses():
    if 'admin_id' not in session:
        flash('Please login first', 'danger')
        return redirect(url_for('admin_login'))
    
    # Redirect to the Google Sheets responses
    return redirect('https://docs.google.com/spreadsheets/d/1ZcsaJ9CDLkm7T0q9x0xqiV4J1RYIK8WKB0Ff_21NYaA/edit?usp=sharing')

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('error.html', error="Internal server error"), 500

# For Vercel deployment
app.wsgi_app = app.wsgi_app

if __name__ == '__main__':
    app.run(debug=True)
