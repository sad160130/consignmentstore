from app import app

# Required for Vercel serverless deployment
def handler(request, response):
    return app(request, response)