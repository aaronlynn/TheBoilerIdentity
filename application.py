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
from time import sleep
import mysql.connector

pusher = Pusher(
  app_id='662419',
  key='63cda1f62b663027a43e',
  secret='41f10d18b52661669b17',
  cluster='us2',
  ssl=True
)

application = Flask(__name__)
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

def startClock(game, minutes=8):
	time_start = time.time()
	seconds = 0
	while seconds <= 60 * minutes and games[game]['clock']:
		pusher.trigger(game, 'clock', {'time': time.strftime("%M:%S", time.gmtime(60 * minutes - seconds))})
		time.sleep(1)
		seconds = int(time.time() - time_start)
	if seconds > 60 * minutes:
		# determine accusation order
		userlist = list(games[game]['players'])
		order = []
		while len(userlist) > 0:
			user = random.choice(userlist)
			order.append(user)
			userlist.remove(user)
		games[game]['order'] = order
		games[game]['current'] = 0
		pusher.trigger(game, 'end-game', {})

@application.route("/")
@application.route("/home")
def home():
	if 'make' in request.args:
		if 'name' not in request.args:
			return render_template('index.html')
		else:
			game = generateRoomId()
			return redirect('/newgame?name=' + request.args['name'] + '&game=' + game)
	if 'join' in request.args:
		if 'name' not in request.args:
			return render_template('index.html')
		else:
			return redirect('/joingame?name=' + request.args['name'])
	return render_template('index.html')

@application.route("/newgame")
def newgame():

	if 'name' not in request.args or 'game' not in request.args:
		return render_template('newgame.html', response='')
	game = request.args['game']

	#TODO handle if host or guest refreshes page. Currently recreates room with same room code but no players

	#create user in database if one doesn't exist
	db = mysql.connector.connect(host='tbi-inst1.cbas20bxl7ak.us-east-2.rds.amazonaws.com', user='root', password='password', database='tbidata') 
	dbuser = request.args['name']
	dbcursor = db.cursor()
	dbcursor.execute('SELECT COUNT(name) FROM tbidata.score WHERE name = "' + dbuser + '";')
	exists = dbcursor.fetchone()

	if exists[0] < 1:
		dbcursor.execute('INSERT INTO tbidata.score (name) VALUES ("' + dbuser + '");')
		db.commit()
	#end db

	games[game] = {'players': {request.args['name']: ''}, 'owner': request.args['name'], 'has_accused': [], 'clock': True}
	return render_template('lobby.html', player=request.args['name'], game_id=game, game=games[game]['players'], is_owner=True)

@application.route("/lobby")
def lobby():
	return render_template('lobby.html')

@application.route("/leavegame")
def leavegame():
	game = request.args['game']
	username = request.args['user']

	if game not in games:
		return redirect(url_for('home'))

	if len(list(games[game]['players'])) == 1:
		del games[game]
		return redirect(url_for('home'))

	if username == games[game]['owner']:
		del games[game]['players'][username]
		newhost = random.choice(list(games[game]['players']))
		games[game]['owner'] = newhost
		pusher.trigger(game, 'leave-game', {'user': username, 'newhost': newhost})

	if username in games[game]['players']:
		del games[game]['players'][username]
		pusher.trigger(game, 'leave-game', {'user': username})

	return redirect(url_for('home'))

@application.route("/joingame")
def joingame():
	found_game = ''
	if 'game' not in request.args and 'name' not in request.args:
		return render_template('joingame.html', found_game='')

	if 'name' in request.args and 'game' not in request.args:
		# print("Join game name: " + urllib.parse.quote(request.args['name']), file=sys.stderr)
		return render_template('joingame.html', name=urllib.parse.quote(request.args['name']), found_game='')

	game = request.args['game'].upper();
	username = urllib.parse.unquote(request.args['name'])

	#create user in database if one doesn't exist
	db = mysql.connector.connect(host='tbi-inst1.cbas20bxl7ak.us-east-2.rds.amazonaws.com', user='root', password='password', database='tbidata') 
	dbuser = username
	dbcursor = db.cursor()
	dbcursor.execute('SELECT COUNT(name) FROM tbidata.score WHERE name = "' + dbuser + '";')
	exists = dbcursor.fetchone()

	if exists[0] < 1:
		dbcursor.execute('INSERT INTO tbidata.score (name) VALUES ("' + dbuser + '");')
		db.commit()
	#end db

	if game in games:
		if username in games[game]['players']:
			return render_template('joingame.html', found_game=username + ' is already in game!', name=username)
		if len(games[game]['players']) == 8:
			return render_template('joingame.html', found_game='Game is full!', name=username)

		games[game]['players'][username] = ''
		pusher.trigger(game, 'join-game', {'user': username})
		return render_template('lobby.html', player=request.args['name'], game_id=game, game=games[game]['players'], is_owner=False)
	
	return render_template('joingame.html', found_game=game + ' does not exist!', name=request.args['name'])

@application.route("/startgame")
def initgame():
	game = request.args['game']
	userlist = list(games[game]['players'].keys())
	locationlist = request.args['options']
	if locationlist == 'spy':
		games[game]['location_list'] = 'spy'
		location = random.choice(list(locations))
		rolelist = locations[location]
	else:
		games[game]['location_list'] = 'pur'
		location = random.choice(list(purduelocations))
		rolelist = purduelocations[location]

	spy = random.choice(list(userlist))
	userlist.remove(spy)

	games[game]['players'][spy] = 'Spy' #should set role
	games[game]['location'] = location	#sets location
	games[game]['spy'] = spy            #set spy for game lobby

	for user in userlist:
		# print(user, file=sys.stderr)
		role = random.choice(rolelist)
		rolelist.remove(role)
		games[game]['players'][user] = role

	pusher.trigger(game, 'start-game', {})
	startClock(game, minutes=8)

@application.route("/game")
def game():
	if 'game' not in request.args or 'user' not in request.args:
		return redirect(url_for('home'))

	game = request.args['game']
	user = request.args['user']

	locs = []
	if games[game]['location_list'] == 'spy':
		locs = locations
	else:
		locs = purduelocations
	
	if game in games:
		return render_template('game.html', game=games[game], game_id=game, user=user, location=games[game]['location'], role=games[game]['players'][user], players=games[game]['players'], locations=list(locs))

	return redirect(url_for('home'))

@application.route("/accuse")
def accuse():
	accuser = request.args['accuser']
	accused = request.args['accused']
	game = request.args['game']
	games[game]['clock'] = False
	if accuser in games[game]['has_accused']:		# if they are in the list of people that have accused don't
		return "You've already accused this round!"	# allow them to accuse and send the message that they've accused

	games[game]['has_accused'].append(accuser)
	games[game]['vote'] = {'accused': accused, 'accuser': accuser, 'for': 1, 'against': 0} # starts up a vote

	# print(accuser + " has accused " + accused + " in game: " + game, file=sys.stderr)
	pusher.trigger(game, 'accuse', {'accused': accused, 'accuser': accuser}) 
	return ''

@application.route("/vote")
def vote():
	game = request.args['game']
	persuasion = request.args['persuasion'] # one of two values 'for' or 'against'
	games[game]['vote'][persuasion] += 1 	# add the vote to the current vote in the game

	#get spy from db
	db = mysql.connector.connect(host='tbi-inst1.cbas20bxl7ak.us-east-2.rds.amazonaws.com', user='root', password='password', database='tbidata') 
	dbspy = games[game]['spy']
	dbaccuser = games[game]['vote']['accuser']
	dbcursor = db.cursor()

	if games[game]['vote']['for'] + games[game]['vote']['against'] == len(games[game]['players']) - 1:
		# vote is done!
		if games[game]['vote']['for'] == len(games[game]['players']) - 1:
			# unanimous, reveal spy, also the game is over one way or another
			# can maybe add more things to reveal if we want
			won = ''
			if games[game]['vote']['accused'] == games[game]['spy']:
				won = 'The spy has lost! ' + games[game]['vote']['accuser'] + ' correctly guessed it was ' + games[game]['spy'] + "!"
				#update accuser wins/spy losses
				
				dbcursor.execute('UPDATE tbidata.score SET accusewins = accusewins + 1 WHERE name = "' + dbaccuser + '";')
				db.commit()
				dbcursor.execute('UPDATE tbidata.score SET spylosses = spylosses + 1 WHERE name = "' + dbspy + '";')
				db.commit()
			else:
				won = 'The spy has won! Everyone guessed ' + games[game]['vote']['accused'] + ', but it was actually ' + games[game]['spy'] + "!"

				#update spy wins/accuser losses
				dbcursor.execute('UPDATE tbidata.score SET spywins = spywins + 1 WHERE name = "' + dbspy + '";')
				db.commit()
				dbcursor.execute('UPDATE tbidata.score SET accuselosses = accuselosses + 1 WHERE name = "' + dbaccuser + '";')
				db.commit()
			pusher.trigger(game, 'vote-result', {'message': 'Vote was unanimously passed! ' + won})
			games[game]['clock'] = False
			cleanupgame(game)
		else:
			# the vote failed, reset it
			pusher.trigger(game, 'vote-result', {'message': 'Vote failed ' + str(games[game]['vote']['for']) + ' for, ' + str(games[game]['vote']['against']) + ' against'}) 
			games[game]['vote'] = {}
			if 'order' not in games[game]:
				games[game]['clock'] = True
				startClock(game, minutes=8)
			else:
				games[game]['current'] = (games[game]['current'] + 1) % len(games[game]['players'])
				pusher.trigger(game, 'end-game', {'current': games[game]['order'][ games[game]['current'] ]})
	# vote isn't done, do nothing
	return ''

@application.route("/guess")
def guess():
	game = request.args['game']
	location = request.args['location']
	games[game]['clock'] = False

	#get user from db
	db = mysql.connector.connect(host='tbi-inst1.cbas20bxl7ak.us-east-2.rds.amazonaws.com', user='root', password='password', database='tbidata') 
	dbspy = games[game]['spy']
	dbcursor = db.cursor()

	message = 'The Spy, ' + games[game]['spy'] + ', guessed the location was ' + location + ' and they were'
	if location == games[game]['location']:
		pusher.trigger(game, 'spy-reveal', {'message': message + ' correct! The Spy wins!'})

		#update spy wins
		dbcursor.execute('UPDATE tbidata.score SET spywins = spywins + 1 WHERE name = "' + dbspy + '";')
		db.commit()
	else:
		#update spy losses
		dbcursor.execute('UPDATE tbidata.score SET spylosses = spylosses + 1 WHERE name = "' + dbspy + '";')
		db.commit()

		pusher.trigger(game, 'spy-reveal', {'message': message + ' incorrect! The Spy loses!'})
	cleanupgame(game)
	return ''

@application.route("/endgame")
def endgame():
	game = request.args['game']
	user = request.args['user']

	return render_template('endgame.html', order=games[game]['order'], user=user, game_id=game, role=games[game]['players'][user], location=games[game]['location'])

def cleanupgame(game):
	db = mysql.connector.connect(host='tbi-inst1.cbas20bxl7ak.us-east-2.rds.amazonaws.com', user='root', password='password', database='tbidata') 
	dbcursor = db.cursor()
	for dbuser in list(games[game]['players']):
		dbcursor.execute('SELECT spywins FROM tbidata.score WHERE name = "' + dbuser + '";')
		spywins = dbcursor.fetchone()[0]

		dbcursor.execute('SELECT spylosses FROM tbidata.score WHERE name = "' + dbuser + '";')
		spylosses = dbcursor.fetchone()[0]

		dbcursor.execute('SELECT accusewins FROM tbidata.score WHERE name = "' + dbuser + '";')
		accusewins = dbcursor.fetchone()[0]

		dbcursor.execute('SELECT accuselosses FROM tbidata.score WHERE name = "' + dbuser + '";')
		accuselosses = dbcursor.fetchone()[0]

		totalscore = (spywins * 1000) + (spylosses * -500) + (accusewins * 500) + (accuselosses * -1000)
		dbcursor.execute('UPDATE tbidata.score SET totalscore = ' + str(totalscore) + ' WHERE name = "' + dbuser + '";')
		db.commit()

	time.sleep(1)
	del games[game]


@application.route("/statistics")
def statistics():
	db = mysql.connector.connect(host='tbi-inst1.cbas20bxl7ak.us-east-2.rds.amazonaws.com', user='root', password='password', database='tbidata') 
	dbcursor = db.cursor()

	getscores = '''SELECT name, totalscore, spywins, spylosses, accusewins, accuselosses 
				FROM tbidata.score
				WHERE spywins != 0 OR spylosses != 0 
					OR accusewins != 0 OR accuselosses != 0 
					OR totalscore != 0
				ORDER BY totalscore DESC'''

	dbcursor.execute(getscores)
	userstats = dbcursor.fetchall()

	rows = []

	for row in userstats:
		rows.append(row)

	return render_template('statistics.html', rows=rows)