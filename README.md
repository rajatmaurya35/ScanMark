# ScanMark - Smart Attendance System

A modern QR code-based attendance tracking system built with Flask and Supabase.

## Features

- QR Code Based Attendance
- Admin Dashboard
- Secure Token System
- Real-time Attendance Tracking
- Mobile-friendly Interface

## Vercel Deployment

1. Fork and Clone:
   ```bash
   git clone https://github.com/your-username/ScanMark.git
   cd ScanMark
   ```

2. Create Vercel Project:
   - Go to [Vercel Dashboard](https://vercel.com)
   - Import your GitHub repository
   - Choose Python framework preset

3. Configure Environment Variables:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon key
   - `FLASK_SECRET_KEY`: A secure random string

4. Deploy:
   ```bash
   vercel
   ```

## Environment Variables

Required environment variables:
```env
FLASK_ENV=production
FLASK_APP=app.py
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-key
FLASK_SECRET_KEY=your-secure-secret
```

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up environment variables:
   - Create a `.env` file
   - Add required environment variables

3. Run the app:
   ```bash
   python app.py
   ```

## Database Schema

1. admins
   - username (text): Primary key
   - password_hash (text): Hashed password
   - created_at (timestamp)

2. attendance
   - student_id (text): Foreign key
   - date (timestamp)
   - status (text)
   - created_at (timestamp)

3. qr_tokens
   - token (text): Primary key
   - session (text)
   - created_at (timestamp)
   - expires_at (timestamp)

## Testing Progress

✅ Admin Authentication
- Login system working
- Password hashing implemented
- Session management secure

✅ QR Code Generation
- Successfully generating QR codes
- QR codes contain proper URL with token
- QR codes are refreshed with timestamp

✅ Attendance Form
- Form loads correctly
- Student ID validation working
- Success/Error pages implemented

## License

MIT License
