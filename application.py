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
from purduelocations import *
import sys
import urllib

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

	games[game] = {'players': {request.args['name']: ''}, 'owner': request.args['name'], 'has_accused': []}
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
		# print("Join game name: " + urllib.parse.quote(request.args['name']), file=sys.stderr)
		return render_template('joingame.html', name=urllib.parse.quote(request.args['name']), found_game='')

	game = request.args['game']
	username = urllib.parse.unquote(request.args['name'])

	if game in games:
		if username in games[game]['players']:
			return render_template('joingame.html', found_game=username + ' is already in game!', name=username)
		if len(games[game]['players']) == 8:
			return render_template('joingame.html', found_game='Game is full!', name=username)

		games[game]['players'][username] = ''
		pusher.trigger(game, 'join-game', {'user': username})
		return render_template('lobby.html', player=request.args['name'], game_id=game, game=games[game]['players'], is_owner=False)
	
	return render_template('joingame.html', found_game=game + ' does not exist!', name=request.args['name'])

@app.route("/startgame")
def initgame():
	game = request.args['game']
	userlist = list(games[game]['players'].keys())
	if True:
		location = random.choice(list(locations))
	else:
		location = random.choice(list(purduelocations))

	rolelist = locations[location]
	spy = random.choice(list(userlist))
	userlist.remove(spy)

	games[game]['players'][spy] = 'Spy' #should set role
	games[game]['location'] = location	#sets location
	games[game]['spy'] = spy            #set spy for game lobby

	for user in userlist:
		print(user, file=sys.stderr)
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
		#TODO game logic goes here. Send location and role to player.
		
		return render_template('game.html', game=games[game], game_id=game, user=user, location=games[game]['location'], role=games[game]['players'][user], players=games[game]['players'])

	return redirect(url_for('home'))

@app.route("/accuse")
def accuse():
	accuser = request.args['accuser']
	accused = request.args['accused']
	game = request.args['game']
	if accuser in games[game]['has_accused']:		# if they are in the list of people that have accused don't
		return "You've already accused this round!"	# allow them to accuse and send the message that they've accused

	games[game]['has_accused'].append(accuser)
	games[game]['vote'] = {'accused': accused, 'accuser': accuser, 'for': 0, 'against': 0} # starts up a vote

	# print(accuser + " has accused " + accused + " in game: " + game, file=sys.stderr)
	pusher.trigger(game, 'accuse', {'accused': accused, 'accuser': accuser}) 
	return ''

@app.route("/vote")
def vote():
	game = request.args['game']
	persuasion = request.args['persuasion'] # one of two values 'for' or 'against'
	games[game]['vote'][persuasion] += 1 	# add the vote to the current vote in the game
	if games[game]['vote']['for'] + games[game]['vote']['against'] == len(games[game]['players']):
		# vote is done!
		if games[game]['vote']['for'] == len(games[game]['players']):
			# unanimous, reveal spy, also the game is over one way or another
			# can maybe add more things to reveal if we want
			won = ''
			if games[game]['vote']['accused'] == games[game]['spy']:
				won = 'The spy has lost! ' + games[game]['vote']['accuser'] + ' correctly guessed it was ' + games[game]['spy']
			else:
				won = 'The spy has won! It was ' + games[game]['spy']
			pusher.trigger(game, 'vote-result', {'message': 'Vote was unanimously passed! ' + won})
			del games[game]
		else:
			# the vote failed, reset it
			pusher.trigger(game, 'vote-result', {'message': 'Vote failed ' + str(games[game]['vote']['for']) + ' for, ' + str(games[game]['vote']['against']) + ' against'}) 
			games[game]['vote'] = {}
	# vote isn't done, do nothing
	return ''

@app.route("/pushertest/<name>")
def pushertest(name):
	pusher.trigger('my-channel', 'my-event', {'message': 'hello ' + name})
	return "Pushed " + name

@app.route("/pusherpage")
def pusherpage():
	return render_template("pushertest.html")