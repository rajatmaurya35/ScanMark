from app import app

# This is for Vercel deployment
def handler(event, context):
    return app(event, context)
