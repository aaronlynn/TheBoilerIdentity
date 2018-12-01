from flask import Flask
from flask import render_template
app = Flask(__name__)

@app.route("/")
def hello():
    return 'Hello World!<a href="/home">Home</a>'

@app.route("/home")
def home():
	return render_template('temphome.html')