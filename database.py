import os
from supabase import create_client, Client

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv('SUPABASE_URL', ''),
    os.getenv('SUPABASE_KEY', '')
)

def init_supabase():
    """Initialize Supabase tables"""
    # Create students table
    supabase.table('students').create({
        'id': 'int8',
        'student_id': 'varchar',
        'name': 'varchar',
        'registered_on': 'timestamp'
    })

    # Create attendances table
    supabase.table('attendances').create({
        'id': 'int8',
        'student_id': 'int8',
        'date': 'timestamp',
        'status': 'varchar',
        'location': 'varchar'
    })

    # Create qr_tokens table
    supabase.table('qr_tokens').create({
        'id': 'int8',
        'token': 'varchar',
        'expiry': 'timestamp',
        'created_at': 'timestamp'
    })
