from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
import uuid
from datetime import datetime, timedelta
from functools import lru_cache
import time
import os
import hashlib
import base64
import traceback

# Initialize Supabase client
print("Initializing Supabase client...")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check if Supabase configuration is present
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError('Supabase configuration missing. Please check your .env file.')

try:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print('Error: SUPABASE_URL or SUPABASE_KEY is empty')
        print(f'SUPABASE_URL: {"`" + SUPABASE_URL + "`" if SUPABASE_URL else "Not set"}')
        print(f'SUPABASE_KEY length: {len(SUPABASE_KEY) if SUPABASE_KEY else "Not set"}')
        raise ValueError('Supabase configuration missing or invalid')

    # Test the connection
    print('Testing Supabase connection...')
    test = supabase.table('sessions').select('count', count='exact').execute()
    print('Supabase connection successful!')
except Exception as e:
    print(f'Error connecting to Supabase: {str(e)}')
    print('Please check your .env file and make sure SUPABASE_URL and SUPABASE_KEY are set correctly')
    raise

class Database:
    # Cache admin data for 5 minutes to reduce database load
    @staticmethod
    @lru_cache(maxsize=128, typed=False)
    def _get_admin_cached(username: str, timestamp: int) -> dict:
        data = supabase.table('admins').select('*').eq('username', username).execute()
        return data.data[0] if data.data else None

    @staticmethod
    def test_connection():
        """Test the connection to Supabase"""
        try:
            print("Testing Supabase connection...")
            data = supabase.table('admins').select('*').limit(1).execute()
            print("Connection test successful")
            return True
        except Exception as e:
            print(f"Error connecting to Supabase: {str(e)}")
            return False

    @staticmethod
    def get_admin(username: str) -> dict:
        """Get admin by username"""
        try:
            print(f"Getting admin with username: {username}")
            data = supabase.table('admins').select('*').eq('username', username).execute()
            print(f"Query result: {data.data}")
            
            if data.data:
                return data.data[0]
            return None
        except Exception as e:
            print(f"Error getting admin: {str(e)}")
            traceback.print_exc()
            return None

    @staticmethod
    def create_admin(username: str, password_hash: str) -> bool:
        """Create or update admin user"""
        try:
            # Check if admin exists
            print(f"Checking if admin '{username}' exists...")
            existing = Database.get_admin(username)
            
            if existing:
                print("Admin exists, updating password...")
                data = supabase.table('admins').update({
                    'password_hash': password_hash
                }).eq('username', username).execute()
            else:
                print("Creating new admin...")
                data = supabase.table('admins').insert({
                    'username': username,
                    'password_hash': password_hash,
                    'created_at': 'now()'
                }).execute()
            
            return True
        except Exception as e:
            print(f"Error creating/updating admin: {str(e)}")
            traceback.print_exc()
            return False

    @staticmethod
    def get_sessions() -> list:
        """Get all sessions"""
        try:
            data = supabase.table('sessions').select('*').order('created_at', desc=True).execute()
            return data.data if data.data else []
        except Exception as e:
            print(f"Error getting sessions: {str(e)}")
            return []

    @staticmethod
    def get_session_by_name(session_name: str) -> dict:
        """Get session by name"""
        try:
            data = supabase.table('sessions').select('*').eq('name', session_name).execute()
            return data.data[0] if data.data else None
        except Exception as e:
            print(f"Error getting session by name: {str(e)}")
            return None

    @staticmethod
    def create_session(session_data: dict) -> tuple[bool, str]:
        """Create a new session
        Returns: (success: bool, token: str)
        """
        try:
            # Validate input
            name = session_data.get('name')
            faculty = session_data.get('faculty')
            if not name or not faculty:
                print("Missing required fields: name or faculty")
                return False, ""

            # Create session
            session_id = str(uuid.uuid4())
            session = {
                'id': session_id,
                'name': name,
                'faculty': faculty,
                'branch': session_data.get('branch', 'Unknown'),
                'semester': session_data.get('semester', 'Unknown'),
                'created_at': datetime.now().isoformat(),
                'active': True
            }
            
            # Insert session
            session_result = supabase.table('sessions').insert(session).execute()
            if not session_result.data:
                print("Failed to create session record")
                return False, ""
            
            # Create QR token
            token = str(uuid.uuid4())
            token_data = {
                'token': token,
                'session': name,  # Use session name
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
            }
            
            # Insert token
            token_result = supabase.table('qr_tokens').insert(token_data).execute()
            if not token_result.data:
                print("Failed to create QR token")
                # Clean up session if token creation fails
                supabase.table('sessions').delete().eq('id', session_id).execute()
                return False, ""
                
            return True, token
            
        except Exception as e:
            print(f"Error creating session: {str(e)}")
            traceback.print_exc()
            return False, ""

    @staticmethod
    def get_session(session_id: str) -> dict:
        """Get session details by ID"""
        try:
            data = supabase.table('sessions').select('*').eq('id', session_id).execute()
            return data.data[0] if data.data else None
        except Exception as e:
            print(f"Error getting session: {str(e)}")
            return None

    @staticmethod
    def get_responses(session_id: str) -> list:
        """Get responses for a session"""
        try:
            # Get QR tokens for the session
            tokens = supabase.table('qr_tokens').select('token').eq('session', session_id).execute()
            if not tokens.data:
                return []
            
            # Get all token values
            token_values = [t['token'] for t in tokens.data]
            
            # Get attendance records for these tokens
            data = supabase.table('attendance').select('*').in_('token', token_values).order('created_at', desc=True).execute()
            return data.data if data.data else []
        except Exception as e:
            print(f"Error getting responses: {str(e)}")
            return []

    @staticmethod
    def delete_session(session_id: str) -> bool:
        """Delete a session and its QR tokens by ID"""
        try:
            # Get session name first
            session = supabase.table('sessions').select('name').eq('id', session_id).single().execute()
            if not session.data:
                return False
            
            session_name = session.data['name']
            
            # Delete QR tokens for this session
            supabase.table('qr_tokens').delete().eq('session', session_name).execute()
            
            # Delete session
            result = supabase.table('sessions').delete().eq('id', session_id).execute()
            # Clear cache after modification
            Database._get_sessions_cached.cache_clear()
            return bool(result.data)
        except Exception as e:
            print(f"Error deleting session: {str(e)}")
            return False
            
    @staticmethod
    def delete_session_by_name(session_name: str) -> bool:
        """Delete a session and its QR tokens by name"""
        try:
            # Delete QR tokens for this session
            supabase.table('qr_tokens').delete().eq('session', session_name).execute()
            
            # Delete session
            result = supabase.table('sessions').delete().eq('name', session_name).execute()
            # Clear cache after modification
            Database._get_sessions_cached.cache_clear()
            return bool(result.data)
        except Exception as e:
            print(f"Error deleting session by name: {str(e)}")
            return False

    @staticmethod
    def toggle_session(session_id: str) -> bool:
        """Toggle session active status"""
        try:
            # Get current status
            session_result = supabase.table('sessions').select('active').eq('id', session_id).execute()
            if not session_result.data:
                return False
            
            # Toggle status
            current_status = session_result.data[0]['active']
            update_result = supabase.table('sessions')\
                .update({'active': not current_status})\
                .eq('id', session_id)\
                .execute()
                
            # Clear cache after modification
            Database._get_sessions_cached.cache_clear()
            return bool(update_result.data)
        except Exception as e:
            print(f"Error toggling session: {str(e)}")
            return False

    @staticmethod
    def delete_session(session_id: str) -> bool:
        """Delete a session"""
        try:
            data = supabase.table('sessions').delete().eq('id', session_id).execute()
            # Clear cache after modification
            Database._get_sessions_cached.cache_clear()
            return bool(data.data)
        except Exception as e:
            print(f"Error deleting session: {str(e)}")
            return False

    # Cache QR token verification for 5 seconds
    @staticmethod
    @lru_cache(maxsize=1000, typed=False)
    def _verify_qr_token_cached(token: str, timestamp: int) -> dict:
        data = supabase.table('qr_tokens').select('*').eq('token', token).execute()
        if not data.data:
            return None
        token_data = data.data[0]
        if datetime.fromisoformat(token_data['expires_at']) < datetime.now():
            return None
        return token_data

    @staticmethod
    def verify_qr_token(token: str) -> dict:
        """Verify if a QR token is valid and not expired with caching"""
        try:
            # Use current 5-second block as cache key
            timestamp = int(time.time() / 5) * 5
            return Database._verify_qr_token_cached(token, timestamp)
        except Exception as e:
            print(f"Error verifying QR token: {str(e)}")
            return None

    @staticmethod
    def create_qr_token(session: str, expires_in_minutes: int = 60) -> dict:
        """Create a new QR token for a session"""
        try:
            token = str(uuid.uuid4())
            data = supabase.table('qr_tokens').insert({
                'token': token,
                'session': session,
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(minutes=expires_in_minutes)).isoformat()
            }).execute()
            return data.data[0] if data.data else None
        except Exception as e:
            print(f"Error creating QR token: {str(e)}")
            return None

    # Cache attendance stats for 1 minute
    @staticmethod
    @lru_cache(maxsize=1, typed=False)
    def _get_attendance_stats_cached(timestamp: int) -> dict:
        total = supabase.table('attendance').select('count', count='exact').execute()
        today = datetime.now().date().isoformat()
        today_count = supabase.table('attendance').select('count', count='exact').gte('created_at', today).execute()
        students = supabase.table('attendance').select('student_id').execute()
        unique_students = len(set(record['student_id'] for record in students.data))
        
        return {
            'total_attendance': total.count if hasattr(total, 'count') else 0,
            'today_attendance': today_count.count if hasattr(today_count, 'count') else 0,
            'total_students': unique_students
        }

    @staticmethod
    def get_attendance_stats() -> dict:
        """Get attendance statistics with caching"""
        try:
            # Use current 1-minute block as cache key
            timestamp = int(time.time() / 60) * 60
            return Database._get_attendance_stats_cached(timestamp)
        except Exception as e:
            print(f"Error getting attendance stats: {str(e)}")
            return {
                'total_attendance': 0,
                'today_attendance': 0,
                'total_students': 0
            }

    # Cache attendance trends for 5 minutes
    @staticmethod
    @lru_cache(maxsize=1, typed=False)
    def _get_attendance_trends_cached(days: int, timestamp: int) -> list:
        try:
            trends = []
            for i in range(days - 1, -1, -1):
                date = (datetime.now() - timedelta(days=i)).date()
                next_date = date + timedelta(days=1)
                
                count = supabase.table('attendance').select('count', count='exact')\
                    .gte('created_at', date.isoformat())\
                    .lt('created_at', next_date.isoformat())\
                    .execute()
                
                trends.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'count': count.count if hasattr(count, 'count') else 0
                })
            return trends
        except Exception as e:
            print(f"Error in _get_attendance_trends_cached: {str(e)}")
            return []

    @staticmethod
    def get_attendance_trends(days: int = 7) -> list:
        """Get attendance trends for the specified number of days"""
        try:
            # Use current 5-minute block as cache key
            timestamp = int(time.time() / 300) * 300
            return Database._get_attendance_trends_cached(days, timestamp)
        except Exception as e:
            print(f"Error getting attendance trends: {str(e)}")
            return []

    @staticmethod
    def mark_attendance(student_id: str, session_id: str = None) -> dict:
        """Mark attendance for a student"""
        try:
            # Validate session if provided
            if session_id:
                session = Database.get_session(session_id)
                if not session or not session['active']:
                    raise ValueError("Invalid or inactive session")

            data = supabase.table('attendance').insert({
                'id': str(uuid.uuid4()),
                'student_id': student_id,
                'session_id': session_id,
                'created_at': datetime.now().isoformat(),
                'status': 'present'
            }).execute()
            # Clear stats cache after new attendance
            Database._get_attendance_stats_cached.cache_clear()
            Database._get_attendance_trends_cached.cache_clear()
            return data.data[0] if data.data else None
        except ValueError as ve:
            print(f"Validation error in mark_attendance: {str(ve)}")
            raise
        except Exception as e:
            print(f"Error marking attendance: {str(e)}")
            return None

    @staticmethod
    def get_unique_students_count():
        """Get count of unique students who have attended sessions."""
        try:
            data = supabase.table('attendance').select('student_id', count='exact').execute()
            return data.count
        except Exception as e:
            print(f"Error getting unique students count: {str(e)}")
            return 0

    @staticmethod
    def get_active_sessions_count():
        """Get count of active sessions."""
        try:
            now = datetime.now()
            data = supabase.table('qr_tokens').select('session', count='exact').gte('expires_at', now.isoformat()).execute()
            return data.count
        except Exception as e:
            print(f"Error getting active sessions count: {str(e)}")
            return 0

    @staticmethod
    def get_today_attendance_count():
        """Get count of attendance records for today."""
        try:
            today = datetime.now().date()
            data = supabase.table('attendance').select('id', count='exact').gte('created_at', today.isoformat()).execute()
            return data.count
        except Exception as e:
            print(f"Error getting today's attendance count: {str(e)}")
            return 0

    @staticmethod
    def get_total_attendance_count():
        """Get total count of attendance records."""
        try:
            data = supabase.table('attendance').select('id', count='exact').execute()
            return data.count
        except Exception as e:
            print(f"Error getting total attendance count: {str(e)}")
            return 0

    @staticmethod
    def get_session_events():
        """Get session events for calendar."""
        try:
            # Get all active sessions
            now = datetime.now()
            data = supabase.table('qr_tokens').select('session,created_at,expires_at').gte('expires_at', now.isoformat()).execute()
            
            events = []
            for record in data.data:
                events.append({
                    'title': record['session'],
                    'start': record['created_at'],
                    'end': record['expires_at'],
                    'allDay': False
                })
            
            return events
        except Exception as e:
            print(f"Error getting session events: {str(e)}")
            return []
