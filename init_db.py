from app import app, db
from flask import Flask

def init_db():
    with app.app_context():
        # Create all database tables
        db.create_all()
        print("Database tables created successfully!")

if __name__ == '__main__':
    init_db()
