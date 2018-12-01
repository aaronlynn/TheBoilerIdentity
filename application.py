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

@app.route("/newgame")
def newgame():
	return render_template('newgame.html')

@app.route("/lobby")
def lobby():
	return render_template('lobby.html')

@app.route("/joingame")
def joingame():
	return render_template('joingame.html')

@app.route("/game")
def game():
	return render_template('game.html')