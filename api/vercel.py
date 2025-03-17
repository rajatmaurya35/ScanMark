from flask import Flask
from app import app as flask_app

app = Flask(__name__)
app.wsgi_app = flask_app.wsgi_app

# Import all routes and models
from app import db, Student, Attendance, QRToken

# Create tables on startup
with app.app_context():
    try:
        db.create_all()
        print("Database tables created successfully!")
    except Exception as e:
        print(f"Error creating tables: {str(e)}")

def handler(request):
    """Handle requests in Vercel serverless function"""
    return app(request)
