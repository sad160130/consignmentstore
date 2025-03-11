from flask import Flask

app = Flask(__name__)

@app.route('/api/hello')
def api_hello():
    return {"message": "Hello from Flask!"}

@app.route('/')
def home():
    return "Welcome to Consignment Store Directory!"