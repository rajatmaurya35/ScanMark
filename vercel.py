from app import app

# This is the handler that Vercel will use
def handler(request, context):
    return app(request)
