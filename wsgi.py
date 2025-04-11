from app import app

# This is for Vercel deployment
def handler(request, context):
    return app
