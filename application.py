from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)

@app.route("/")
@app.route("/home")
def home():
	return render_template('temphome.html')

@app.route("/hello/<name>")
def hello(name):
	return render_template('hello.html', name=name)