-- Drop existing tables if they exist
DROP TABLE IF EXISTS public.attendance CASCADE;
DROP TABLE IF EXISTS public.qr_tokens CASCADE;
DROP TABLE IF EXISTS public.admins CASCADE;

-- Create admins table
CREATE TABLE public.admins (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Create qr_tokens table
CREATE TABLE public.qr_tokens (
    token TEXT PRIMARY KEY,
    session TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create attendance table
CREATE TABLE public.attendance (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    student_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    status TEXT DEFAULT 'present'
);

-- Create initial admin user (password: admin123)
INSERT INTO public.admins (username, password_hash) 
VALUES ('admin', 'pbkdf2:sha256:600000$7NEr7GfqsN1nEHCB$d2f5495e6f5c3f7c0c71f7730eac784d7675e60d5b6f2e43146ef71dfdc6');
