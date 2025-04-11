from dotenv import load_dotenv
import os

load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# App Configuration
SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24).hex())
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
