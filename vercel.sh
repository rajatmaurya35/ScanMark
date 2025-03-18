#!/bin/bash

# Install dependencies
pip install -r requirements.txt

# Run database migrations
python -c "from app import db; db.create_all()"

# Start the application
gunicorn app:app
