from flask import Flask
from app import app

# Required for Vercel serverless deployment
def handler(request):
    return app(request)