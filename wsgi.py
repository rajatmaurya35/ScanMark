from app import app

# For Vercel deployment
def handler(environ, start_response):
    return app(environ, start_response)
