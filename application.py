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
games = {}

@app.route("/")
@app.route("/home")
def home():
	return render_template('index.html')

@app.route("/hello/<name>")
def hello(name):
	return render_template('hello.html', name=name)

@app.route("/newgame")
def newgame():
	if 'game' not in request.form or 'user' not in request.form:
		return render_template('newgame.html', response='')

	if request.form['game'] in games:
		return render_template('newgame.html', response='Game already exists!')

	games[request.form['game']] = [request.form['user']]
	return render_template('lobby.html', game_id=request.form['game'], game=[request.form['user']])

@app.route("/joingame")
def joingame():
	found_game = ''
	if 'game' not in request.form or 'user' not in request.form:
		return render_template('joingame.html', found_game='')

	game = request.form['game']
	username = request.args['user']
	if game in games:
		if username in games[game]:
			return render_template('joingame.html', found_game=username + ' already in game!')
		else:
			games[game].append(username)
			pusher.trigger(game, 'join-game', {'user': username})
			return render_template('lobby.html', game_id=game, game=games[game])
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