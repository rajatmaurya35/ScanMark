from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_session import Session
from supabase import create_client
import os
import segno
import base64
from io import BytesIO

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

# Initialize Supabase client
supabase_url = os.environ.get('SUPABASE_URL', 'https://aaluawvcohqfhevkdnuv.supabase.co')
supabase_key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhbHVhd3Zjb2hxZmhldmtkbnV2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNzY3MzcsImV4cCI6MjA1Nzg1MjczN30.kKL_B4sw1nwY6lbzgyPHQYoC_uqDsPkT51ZOnhr6MNA')
supabase = create_client(supabase_url, supabase_key)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        try:
            response = supabase.table('admins').select("*").eq('username', username).execute()
            if response.data and len(response.data) > 0:
                user = response.data[0]
                if password == user['password_hash']:  # In production, use proper password hashing
                    session['user'] = username
                    return jsonify({"success": True})
            return jsonify({"success": False, "message": "Invalid credentials"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
    
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin/dashboard.html')

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr():
    if 'user' not in session:
        return jsonify({"success": False, "message": "Not authenticated"})
    
    data = request.get_json()
    session_str = f"{data['session']} - {data['faculty']} - {data['branch']} - {data['semester']}"
    
    # Generate QR code
    qr = segno.make(session_str)
    buffer = BytesIO()
    qr.save(buffer, kind='png', scale=10)
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return jsonify({
        "success": True,
        "qr": qr_base64,
        "session": session_str
    })

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(debug=True)
