from app import app

# For local development
if __name__ == "__main__":
    app.run()

# For Vercel serverless
def handler(environ, start_response):
    return app(environ, start_response)
