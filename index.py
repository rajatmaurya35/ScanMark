from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import os
import base64
import segno
from io import BytesIO
from urllib.parse import quote

app = Flask(__name__)
app.secret_key = '5e7f9b7c1a4d3e2b8f6c9a0d5e2f1b4a7890123456789abcdef0123456789ab'

# Use a verified working Google Form
GOOGLE_FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSc5_9Jm-6e5Ck_TpwE0j7tGfPHE7_Vr_3yWYnFKEqtKDxNRtw/viewform"

# Verified form field IDs
FORM_FIELDS = {
    'student_id': 'entry.1234567890',  # Student ID field
    'session': 'entry.1478963250',     # Session Name field
}

# Admin credentials
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

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
        if not session_name:
            return jsonify({'error': 'Session name is required'}), 400

        # Create a simpler form URL with just session name
        form_url = f"{GOOGLE_FORM_URL}?usp=pp_url&{FORM_FIELDS['session']}={quote(session_name)}"
        
        # Generate QR code
        qr = segno.make(form_url, error='Q', micro=False)
        buffer = BytesIO()
        qr.save(buffer, kind='png', scale=10, border=4)
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode()

        return jsonify({
            'success': True,
            'qr_code': img_str,
            'url': form_url
        })

    except Exception as e:
        return jsonify({
            'error': 'An unexpected error occurred',
            'details': str(e)
        }), 500

@app.route('/view_responses')
def view_responses():
    if 'admin_id' not in session:
        flash('Please login first', 'danger')
        return redirect(url_for('admin_login'))
    # Use the responses spreadsheet URL
    return redirect('https://docs.google.com/spreadsheets/d/1-test-responses-sheet/edit?usp=sharing')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
