from app import app, db

# Create tables on startup
with app.app_context():
    db.create_all()
    print("Database tables created successfully!")

# Vercel requires a handler function
def handler(request, context):
    return app(request)
