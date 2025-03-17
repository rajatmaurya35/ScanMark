# ScanMark - Smart Attendance System

A modern attendance tracking system with QR code scanning, biometric verification, and location tracking.

## Features

- QR Code Based Attendance
- Face Recognition
- Fingerprint Verification
- Location Tracking
- Student Dashboard with Statistics
- Secure Token System

## Vercel Deployment

1. Deploy via Vercel Dashboard:
   - Import your GitHub repository
   - Configure environment variables
   - Click Deploy

## Environment Variables

Required environment variables:
```
FLASK_ENV=production
SECRET_KEY=your-secure-secret-key
DATABASE_URL=your-database-url
```

## Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the app:
```bash
python app.py
```

## Testing Progress

✅ QR Code Generation
- Successfully generating QR codes
- QR codes contain proper URL with token
- QR codes are refreshed with timestamp

✅ Attendance Form
- Form loads correctly
- Location access working
- Form validation in place
- Success/error messages showing

✅ Student Dashboard
- Statistics display working
- Attendance history showing
- Location tracking enabled
- Navigation working
