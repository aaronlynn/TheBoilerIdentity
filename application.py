from flask import Flask
from flask import render_template
app = Flask(__name__)

@app.route("/")
def hello():
    return 'Hello World!<a href="/home">Home</a>'

@app.route("/home")
def home():
	return render_template('temphome.html')

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