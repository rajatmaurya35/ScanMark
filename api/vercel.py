from app import app

# Vercel requires a handler function
def handler(request, context):
    return app(request)
