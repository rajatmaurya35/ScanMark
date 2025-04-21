# Import the Flask application
from app import app as application

# For local development
if __name__ == '__main__':
    application.run()

# For Render deployment
app = application
