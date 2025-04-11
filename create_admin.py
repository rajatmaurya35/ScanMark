from database import Database
import hashlib
import os
import base64

def hash_password(password: str) -> str:
    """Hash password with salt using PBKDF2"""
    salt = os.urandom(32)  # 32 bytes salt
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return base64.b64encode(salt + key).decode('utf-8')

def main():
    print("Starting admin creation/update process...")
    
    # Test database connection
    if not Database.test_connection():
        print("Failed to connect to database. Please check your .env file.")
        return
        
    # Admin credentials
    username = 'admin'
    password = 'admin123'
    
    # Hash password
    password_hash = hash_password(password)
    
    # Create or update admin
    if Database.create_admin(username, password_hash):
        print("Admin created/updated successfully!")
        
        # Verify admin exists
        admin = Database.get_admin(username)
        if admin:
            print("Verified: Admin exists in database")
        else:
            print("Error: Could not verify admin in database")
    else:
        print("Error: Failed to create/update admin")

if __name__ == '__main__':
    main()
