# Import the Flask application
from app import app as application

# For local development
if __name__ == '__main__':
    application.run(host='0.0.0.0', port=5000)

# For Render deployment
app = application
