-- Function to create students table
CREATE OR REPLACE FUNCTION create_students_table()
RETURNS void AS $$
BEGIN
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
END;
$$ LANGUAGE plpgsql;

-- Function to create admins table
CREATE OR REPLACE FUNCTION create_admins_table()
RETURNS void AS $$
BEGIN
    CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
END;
$$ LANGUAGE plpgsql;

-- Function to create attendance table
CREATE OR REPLACE FUNCTION create_attendance_table()
RETURNS void AS $$
BEGIN
    CREATE TABLE IF NOT EXISTS attendance (
        id SERIAL PRIMARY KEY,
        student_id TEXT REFERENCES students(student_id),
        status TEXT NOT NULL CHECK (status IN ('present', 'absent')),
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
END;
$$ LANGUAGE plpgsql;

-- Function to create qr_tokens table
CREATE OR REPLACE FUNCTION create_qr_tokens_table()
RETURNS void AS $$
BEGIN
    CREATE TABLE IF NOT EXISTS qr_tokens (
        token TEXT PRIMARY KEY,
        session TEXT NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL
    );
END;
$$ LANGUAGE plpgsql;
