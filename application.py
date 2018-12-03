from flask import Flask
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
import time
import string
import random
import json
from pusher import Pusher
from locations import *


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
	returned = ''
	for i in range(0, 4):
		returned += random.choice(string.ascii_uppercase)
	while returned in games:
		returned = ''
		for i in range(0, 4):
			returned += random.choice(string.ascii_uppercase)
	return returned

def startClock(game, minutes=1):
	time_start = time.time()
	seconds = 0
	while seconds <= 60 * minutes:
		pusher.trigger(game, 'clock', {'time': time.strftime("%M:%S", time.gmtime(60 * minutes - seconds))})
		time.sleep(1)
		seconds = int(time.time() - time_start)
	pusher.trigger(game, 'end-game', {})

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

	games[game] = {'players': {request.args['name']: ''}, 'owner': request.args['name']}
	return render_template('lobby.html', player=request.args['name'], game_id=game, game=games[game]['players'], is_owner=True)

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
		if username in games[game]['players']:
			return render_template('joingame.html', found_game=username + ' is already in game!')
		else:
			games[game]['players'][username] = ''
			pusher.trigger(game, 'join-game', {'user': username})
			return render_template('lobby.html', player=request.args['name'], game_id=game, game=games[game]['players'], is_owner=False)
	return render_template('joingame.html', found_game=game + ' does not exist!', name=request.args['name'])

@app.route("/startgame")
def initgame():
	game = request.args['game']
	userlist = games[game]['players']
	location = random.choice(list(locations))
	rolelist = locations[location]
	spy = random.choice(list(userlist))
	userlist[spy]

	games[game]['location'] = location
	games[game]['spy'] = spy

	for user in userlist:
		role = random.choice(rolelist)
		rolelist.remove(role)
		games[game]['players'][user] = role

	pusher.trigger(game, 'start-game', {})
	startClock(game, minutes=8)

@app.route("/game")
def game():
	if 'game' not in request.args or 'user' not in request.args:
		return redirect(url_for('home'))

	game = request.args['game']
	user = request.args['user']
	if game in games:
		#TODO game logic goes here. Send location and role to player. Start a clock?
		
		return render_template('game.html', game_id=game, user=user)

	return redirect(url_for('home'))

@app.route("/pushertest/<name>")
def pushertest(name):
	pusher.trigger('my-channel', 'my-event', {'message': 'hello ' + name})
	return "Pushed " + name

@app.route("/pusherpage")
def pusherpage():
	return render_template("pushertest.html")