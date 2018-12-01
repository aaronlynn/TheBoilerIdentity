from flask import Flask
from flask import render_template
from flask import request
from pusher import Pusher


pusher = Pusher(
  app_id='662419',
  key='63cda1f62b663027a43e',
  secret='41f10d18b52661669b17',
  cluster='us2',
  ssl=True
)

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

@app.route("/pushertest/<name>")
def pushertest(name):
	pusher.trigger('my-channel', 'my-event', {'message': 'hello ' + name})
	return "Pushed " + name

@app.route("/pusherpage")
def pusherpage():
	return render_template("pushertest.html")