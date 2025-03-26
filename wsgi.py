from app import app

if __name__ == "__main__":
    app.run()

# Vercel handler
def application(environ, start_response):
    return app(environ, start_response)
