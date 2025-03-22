-- Drop existing tables if they exist
DROP TABLE IF EXISTS public.attendance;
DROP TABLE IF EXISTS public.qr_tokens;
DROP TABLE IF EXISTS public.admins;

-- Create qr_tokens table
CREATE TABLE IF NOT EXISTS public.qr_tokens (
    token TEXT PRIMARY KEY,
    session TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create attendance table
CREATE TABLE IF NOT EXISTS public.attendance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'present'
);

-- Create admins table
CREATE TABLE IF NOT EXISTS public.admins (
    username TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create initial admin user with password 'admin123'
INSERT INTO public.admins (username, password_hash)
VALUES ('admin', 'pbkdf2:sha256:260000$gWvaBcZxY9QkGxUp$d76f827a4f07f4a69b47d7f90f14d8fb6eef3f9cfb7d84b8ca6c4e42241619c7')
ON CONFLICT (username) DO NOTHING;
