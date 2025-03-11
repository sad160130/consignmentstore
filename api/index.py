from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Basic route to test
@app.route('/')
def home():
    return "Hello from Flask on Vercel!"

# For Vercel deployment
app = app