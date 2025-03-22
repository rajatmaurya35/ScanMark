-- Drop existing tables if they exist
DROP TABLE IF EXISTS public.attendance;
DROP TABLE IF EXISTS public.qr_tokens;
DROP TABLE IF EXISTS public.admins;

-- Create admins table
CREATE TABLE public.admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create qr_tokens table
CREATE TABLE public.qr_tokens (
    id SERIAL PRIMARY KEY,
    token VARCHAR(255) NOT NULL UNIQUE,
    session VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- Create attendance table
CREATE TABLE public.attendance (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'present'
);

-- Create initial admin user (password: admin123)
INSERT INTO public.admins (username, password_hash) 
VALUES ('admin', 'pbkdf2:sha256:600000$7NEr7GfqsN1nEHCB$d2f5495e6f5c3f7c0c71f7730eac784d7675e60d5b6f2e43146ef71dfdc6');
