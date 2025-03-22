-- Drop existing tables if they exist
DROP TABLE IF EXISTS public.attendances CASCADE;
DROP TABLE IF EXISTS public.qr_tokens CASCADE;
DROP TABLE IF EXISTS public.admins CASCADE;

-- Create admins table
CREATE TABLE public.admins (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create qr_tokens table
CREATE TABLE public.qr_tokens (
    id SERIAL PRIMARY KEY,
    token VARCHAR(100) UNIQUE NOT NULL,
    session VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create attendances table (no foreign key to students)
CREATE TABLE public.attendances (
    id SERIAL PRIMARY KEY,
    student_id VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'present'
);

-- Create indexes for better performance
CREATE INDEX idx_qr_tokens_token ON public.qr_tokens(token);
CREATE INDEX idx_attendances_created_at ON public.attendances(created_at DESC);
