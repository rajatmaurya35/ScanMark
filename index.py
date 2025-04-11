from server import app

# This is for Vercel serverless functions
def handler(request):
    """Handle requests in Vercel serverless function."""
    return app
