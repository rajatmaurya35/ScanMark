-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_id text NOT NULL,
    created_at timestamp NOT NULL DEFAULT now(),
    status text NOT NULL DEFAULT 'present'
);

-- Create qr_tokens table
CREATE TABLE IF NOT EXISTS qr_tokens (
    token text PRIMARY KEY,
    session text NOT NULL,
    created_at timestamp NOT NULL DEFAULT now(),
    expires_at timestamp NOT NULL
);

-- Create admins table
CREATE TABLE IF NOT EXISTS admins (
    username text PRIMARY KEY,
    password_hash text NOT NULL,
    created_at timestamp NOT NULL DEFAULT now()
);

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id text PRIMARY KEY,
    name text NOT NULL,
    faculty text NOT NULL,
    branch text NOT NULL,
    semester text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamp NOT NULL DEFAULT now()
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_attendance_student_id ON attendance(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_created_at ON attendance(created_at);
CREATE INDEX IF NOT EXISTS idx_qr_tokens_expires_at ON qr_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(active);
