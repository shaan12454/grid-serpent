import os
import sqlite3
from flask import Flask, render_template, request, jsonify, session, g
from datetime import datetime
import secrets

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
DB = os.path.join(os.path.dirname(__file__), 'scores.db')

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB, check_same_thread=False)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            name TEXT,
            score INTEGER,
            mode TEXT,
            created_at TEXT
        );
    ''')
    db.commit()

# ✅ Call init_db immediately instead of using before_first_request or before_serving
with app.app_context():
    init_db()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    if 'player_id' not in session:
        session['player_id'] = secrets.token_hex(8)
    return render_template('index.html')

@app.route('/play')
def play():
    if 'player_id' not in session:
        session['player_id'] = secrets.token_hex(8)
    return render_template('play.html')

@app.route('/submit_score', methods=['POST'])
def submit_score():
    data = request.json or {}
    score = int(data.get('score', 0))
    name = data.get('name', 'Player')[:40]
    mode = data.get('mode', 'classic')[:30]
    sid = session.get('player_id', 'anon')
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO scores (session_id,name,score,mode,created_at) VALUES (?,?,?,?,?)',
        (sid, name, score, mode, datetime.utcnow().isoformat())
    )
    db.commit()
    return jsonify({'ok': True})

@app.route('/scores')
def scores():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT name,score,mode,created_at FROM scores ORDER BY score DESC LIMIT 100')
    top = cursor.fetchall()
    sid = session.get('player_id','anon')
    cursor.execute(
        'SELECT name,score,mode,created_at FROM scores WHERE session_id=? ORDER BY created_at DESC LIMIT 20',
        (sid,)
    )
    mine = cursor.fetchall()
    return render_template('scores.html', top=top, mine=mine)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
