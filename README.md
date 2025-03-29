# ScanMark - QR Code Attendance System

A modern QR code-based attendance tracking system that integrates with Google Forms for easy data collection and management.

## Features

- **QR Code Generation**: Create unique QR codes for different sessions
- **Admin Dashboard**: Secure admin interface for managing attendance
- **Google Forms Integration**: Seamless integration with Google Forms for data collection
- **Google Sheets Integration**: View all form submissions in a Google Spreadsheet
- **Mobile-friendly**: Responsive design works on all devices
- **Secure Authentication**: Protected admin access

## Setup

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   Create a `.env` file with:
   ```env
   FLASK_ENV=development
   SECRET_KEY=your-secret-key-here
   ```

3. **Run in Development**:
   ```bash
   python index.py
   ```

4. **Run in Production**:
   ```bash
   # Windows
   start.bat

   # Linux/Mac
   chmod +x start.sh
   ./start.sh
   ```

## Usage

1. **Admin Login**:
   - Default username: `admin`
   - Default password: `admin123`
   - **IMPORTANT**: Change password after first login

2. **Generate QR Codes**:
   - Click "Generate QR" in dashboard
   - Fill in session details
   - Download or display QR code

3. **Track Attendance**:
   - Students scan QR code
   - Form opens automatically
   - Responses recorded in Google Sheet

4. **View Attendance**:
   - Click "View Form History"
   - Access Google Sheet with all records

## Production Deployment

1. **Prerequisites**:
   - Python 3.7+
   - Web server (Nginx/Apache)
   - SSL certificate (for HTTPS)

2. **Environment Variables**:
   ```env
   FLASK_ENV=production
   SECRET_KEY=your-secure-key
   ```

3. **Web Server Configuration (Nginx)**:
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

## Security Notes

1. **Always in Production**:
   - Use HTTPS (SSL/TLS)
   - Change default admin password
   - Set secure SECRET_KEY
   - Enable session security

2. **Best Practices**:
   - Regular security updates
   - Monitor access logs
   - Backup data regularly
   - Rate limit authentication attempts

## License

This project is licensed under the MIT License.
