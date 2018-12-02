from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
import string
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
		returned += random.choice(string.ascii_uppercase)
	while returned in games:
		returned = ''
		for i in range(0, 4):
			returned += random.choice(string.ascii_uppercase)
	return returned

@app.route("/")
@app.route("/home")
def home():
	if 'make' in request.args:
		if 'name' not in request.args:
			return render_template('index.html')
		else:
			return redirect('/newgame?name=' + request.args['name'])
	if 'join' in request.args:
		if 'name' not in request.args:
			return render_template('index.html')
		else:
			return redirect('/joingame?name=' + request.args['name'])
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
	return render_template('lobby.html', game_id=game, game=[request.args['name']], is_owner=True)

@app.route("/lobby")
def lobby():
	return render_template('lobby.html')

@app.route("/joingame")
def joingame():
	found_game = ''
	if 'game' not in request.args and 'name' not in request.args:
		return render_template('joingame.html', found_game='')

	if 'name' in request.args and 'game' not in request.args:
		return render_template('joingame.html', name=request.args['name'], found_game='')

	game = request.args['game']
	username = request.args['name']
	if game in games:
		if username in games[game]:
			return render_template('joingame.html', found_game=username + ' already in game!')
		else:
			games[game]['players'].append(username)
			pusher.trigger(game, 'join-game', {'user': username})
			return render_template('lobby.html', game_id=game, game=games[game], is_owner=False)
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