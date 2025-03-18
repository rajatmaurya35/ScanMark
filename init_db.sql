-- Create students table
CREATE TABLE IF NOT EXISTS students (
    id BIGSERIAL PRIMARY KEY,
    student_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    registered_on TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create attendances table
CREATE TABLE IF NOT EXISTS attendances (
    id BIGSERIAL PRIMARY KEY,
    student_id BIGINT REFERENCES students(id),
    date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'present',
    location VARCHAR(100)
);

-- Create qr_tokens table
CREATE TABLE IF NOT EXISTS qr_tokens (
    id BIGSERIAL PRIMARY KEY,
    token VARCHAR(100) UNIQUE NOT NULL,
    expiry TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_student_id ON students(student_id);
CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendances(date);
CREATE INDEX IF NOT EXISTS idx_token_expiry ON qr_tokens(expiry);
