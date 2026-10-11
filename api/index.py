from flask import Flask
app = Flask(__name__)

@app.route("/")
def home():
    return "VERCEL WORKS - HOME"

@app.route("/auth/login")
def login():
    return "VERCEL WORKS - LOGIN"
