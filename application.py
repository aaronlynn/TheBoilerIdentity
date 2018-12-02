from flask import Flask
from flask import render_template
from flask import request
import random
import json
from pusher import Pusher


pusher = Pusher(
  app_id='662419',
  key='63cda1f62b663027a43e',
  secret='41f10d18b52661669b17',
  cluster='us2',
  ssl=True
)

app = Flask(__name__)
games = {}

def generateRoomId():
	alph = 'ABCDEFGHIJKLMNOPQRSTUVWYZ'
	returned = ''
	for i in range(0, 4):
		returned += alph[random.randint(0, 25)]
	while returned in games:
		returned = ''
		for i in range(0, 4):
			returned += alph[random.randint(0, 25)]
	return returned

@app.route("/")
@app.route("/home")
def home():
	return render_template('index.html')

@app.route("/hello/<name>")
def hello(name):
	return render_template('hello.html', name=name)

@app.route("/newgame")
def newgame():
	if 'name' not in request.args:
		return render_template('newgame.html', response='')
	game = generateRoomId()

	games[game] = {'players': [request.args['name']], 'owner': request.args['name']}
	return render_template('lobby.html', game_id=game, game=json.dumps([request.args['name']]), is_owner=True)

@app.route("/lobby")
def lobby():
	return render_template('lobby.html')

@app.route("/joingame")
def joingame():
	found_game = ''
	if 'game' not in request.form or 'user' not in request.form:
		return render_template('joingame.html', found_game='')

	game = request.form['game']
	username = request.form['user']
	if game in games:
		if username in games[game]:
			return render_template('joingame.html', found_game=username + ' already in game!')
		else:
			games[game]['players'].append(username)
			pusher.trigger(game, 'join-game', {'user': username})
			return render_template('lobby.html', game_id=game, game=json.dumps(games[game]), is_owner=False)
	return render_template('joingame.html', found_game=game + ' does not exist!')

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