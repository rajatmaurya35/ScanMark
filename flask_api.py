import json
import sys
import os
import segno
import base64
from io import BytesIO
from supabase import create_client

# Initialize Supabase client
supabase_url = os.environ.get('SUPABASE_URL', 'https://aaluawvcohqfhevkdnuv.supabase.co')
supabase_key = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFhbHVhd3Zjb2hxZmhldmtkbnV2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDIyNzY3MzcsImV4cCI6MjA1Nzg1MjczN30.kKL_B4sw1nwY6lbzgyPHQYoC_uqDsPkT51ZOnhr6MNA')
supabase = create_client(supabase_url, supabase_key)

def generate_qr(data):
    """Generate a QR code from data and return base64 encoded image"""
    session_str = f"{data['session']} - {data['faculty']} - {data['branch']} - {data['semester']}"
    
    # Generate QR code
    qr = segno.make(session_str)
    buffer = BytesIO()
    qr.save(buffer, kind='png', scale=10)
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return {
        "success": True,
        "qr": qr_base64,
        "session": session_str
    }

def login(data):
    """Handle login request"""
    username = data.get('username')
    password = data.get('password')
    
    try:
        response = supabase.table('admins').select("*").eq('username', username).execute()
        if response.data and len(response.data) > 0:
            user = response.data[0]
            if password == user['password_hash']:  # In production, use proper password hashing
                return {"success": True}
        return {"success": False, "message": "Invalid credentials"}
    except Exception as e:
        return {"success": False, "message": str(e)}

def get_sessions():
    """Get all sessions from database"""
    try:
        response = supabase.table('qr_tokens').select("*").execute()
        return {"success": True, "sessions": response.data}
    except Exception as e:
        return {"success": False, "message": str(e)}

def main():
    """Main function to handle API requests"""
    # Get request data from Node.js
    request_data = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    
    # Determine which API function to call based on request path
    action = request_data.get('action', 'health')
    
    if action == 'generate_qr':
        result = generate_qr(request_data)
    elif action == 'login':
        result = login(request_data)
    elif action == 'get_sessions':
        result = get_sessions()
    else:
        result = {"status": "healthy", "message": "ScanMark API is running!"}
    
    # Return result to Node.js
    print(json.dumps(result))

if __name__ == "__main__":
    main()
