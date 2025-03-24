# ScanMark - QR Code Attendance System

A simple and efficient QR code-based attendance system built with Flask and Supabase.

## Features

- QR Code Generation for Sessions
- Mobile-friendly Student Attendance Form
- Admin Dashboard
- Real-time Attendance Tracking
- Secure Authentication

## Environment Variables

Create a `.env` file with the following variables:

```env
FLASK_SECRET_KEY=your-secret-key
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-anon-key
```

## Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the development server:
   ```bash
   python app.py
   ```

## Deployment on Vercel

1. Fork this repository

2. Create a new project on Vercel
   - Connect your GitHub repository
   - Set the following environment variables in Vercel:
     - `FLASK_SECRET_KEY`
     - `SUPABASE_URL`
     - `SUPABASE_KEY`

3. Deploy!
   - Vercel will automatically detect the Python project
   - The `vercel.json` file handles the configuration

## Database Setup

1. Create a new project on Supabase
2. Run the SQL commands from `schema.sql`
3. Update your environment variables with Supabase credentials

## Default Admin Login

- Username: `admin`
- Password: `admin123`

**Important:** Change the admin password after first login in production!
