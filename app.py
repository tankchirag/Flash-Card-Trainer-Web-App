from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'
 
# Paths to JSON files
DECKS_FILE = 'decks.json'
SCORES_FILE = 'scores.json'
USERS_FILE = 'users.json'
HISTORY_FILE = 'history.json'

# Load data from JSON files
def load_json(file_path, default):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return default

# Save data to JSON files
def save_json(file_path, data):
    with open(file_path, 'w') as f:
        json.dump(data, f)

# Initial data loading
decks = load_json(DECKS_FILE, [])
scores = load_json(SCORES_FILE, {})
users = load_json(USERS_FILE, {})
history = load_json(HISTORY_FILE, {})

def save_data():
    save_json(DECKS_FILE, decks)
    save_json(SCORES_FILE, scores)
    save_json(USERS_FILE, users)
    save_json(HISTORY_FILE, history)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def home():
    return render_template('home.html')
 
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    message = ''
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        if user_id in users:
            message = 'User already exists'
        else:
            users[user_id] = {'password': password, 'quiz_data': {}}
            scores[user_id] = {}  # Initialize scores for the new user
            history[user_id] = {}  # Initialize history for the new user
            save_data()
            flash('User created successfully', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html', message=message)
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        if user_id in users and users[user_id]['password'] == password:
            session['user_id'] = user_id
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html', message=message)
 
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))
 
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        deck_name = request.form['deck_name']
        decks.append({'name': deck_name, 'cards': []})
        save_data()
    return render_template('index.html', decks=decks)
 
@app.route('/edit_deck/<int:deck_index>', methods=['GET', 'POST'])
@login_required
def edit_deck(deck_index):
    deck = decks[deck_index]
    if request.method == 'POST':
        deck['name'] = request.form['deck_name']
        save_data()
    return render_template('edit_deck.html', deck=deck, deck_index=deck_index)
 
@app.route('/edit_card/<int:deck_index>/<int:card_index>', methods=['GET', 'POST'])
@login_required
def edit_card(deck_index, card_index):
    card = decks[deck_index]['cards'][card_index]
    if request.method == 'POST':
        card['question'] = request.form['question']
        card['answer'] = request.form['answer']
        card['hint'] = request.form.get('hint', '')
        save_data()
    return render_template('edit_card.html', card=card, deck_index=deck_index, card_index=card_index)
 
@app.route('/add_card/<int:deck_index>', methods=['POST'])
@login_required
def add_card(deck_index):
    question = request.form['question']
    answer = request.form['answer']
    hint = request.form.get('hint', '')
    decks[deck_index]['cards'].append({'question': question, 'answer': answer, 'hint': hint})
    save_data()
    return redirect(url_for('edit_deck', deck_index=deck_index))
 
@app.route('/delete_card/<int:deck_index>/<int:card_index>', methods=['POST'])
@login_required
def delete_card(deck_index, card_index):
    decks[deck_index]['cards'].pop(card_index)
    save_data()
    return redirect(url_for('edit_deck', deck_index=deck_index))
 
@app.route('/delete_deck/<int:deck_index>', methods=['POST'])
@login_required
def delete_deck(deck_index):
    decks.pop(deck_index)
    save_data()
    return redirect(url_for('index'))
 
@app.route('/start_quiz', methods=['GET', 'POST'])
@login_required
def start_quiz():
    if request.method == 'POST':
        deck_index = int(request.form['deck_index'])
        repetition = int(request.form['repetition'])
        session['deck_index'] = deck_index
        session['repetition'] = repetition
        session['current_card_index'] = 0
        session['card_order'] = [i for i in range(len(decks[deck_index]['cards']))]
        session['correct_answers'] = 0
        session['incorrect_answers'] = 0
        session['unattempted_questions'] = 0
        session['answered_correctly'] = [0] * len(session['card_order'])
        return redirect(url_for('quiz'))
    return render_template('start_quiz.html', decks=decks)
 
@app.route('/quiz', methods=['GET', 'POST'])
@login_required
def quiz():
    deck_index = session['deck_index']
    card_order = session['card_order']
    current_card_index = session['current_card_index']
    repetition = session['repetition']
    if current_card_index >= len(card_order):
        session['current_card_index'] = 0
        current_card_index = 0
    card_index = card_order[current_card_index]
    card = decks[deck_index]['cards'][card_index]
    if request.method == 'POST':
        response = request.form['response']
        user_id = session['user_id']
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if user_id not in history:
            history[user_id] = {}
        if deck_index not in history[user_id]:
            history[user_id][deck_index] = {}
        if card_index not in history[user_id][deck_index]:
            history[user_id][deck_index][card_index] = []
        history[user_id][deck_index][card_index].append({'timestamp': timestamp, 'response': response})

        if response == 'true':
            session['correct_answers'] += 1
            session['answered_correctly'][current_card_index] += 1
        elif response == 'false':
            session['incorrect_answers'] += 1
            session['answered_correctly'][current_card_index] = 0
        elif response == 'skip':
            session['unattempted_questions'] += 1
        elif response == 'quit':
            return redirect(url_for('quiz_complete'))
        if session['answered_correctly'][current_card_index] >= repetition:
            card_order.pop(current_card_index)
            session['answered_correctly'].pop(current_card_index)
        else:
            session['current_card_index'] += 1

        if not card_order:
            return redirect(url_for('quiz_complete'))
        save_data()
        return redirect(url_for('quiz'))
    return render_template('quiz.html', card=card, deck=decks[deck_index], card_index=card_index)
 
@app.route('/show_answer/<int:deck_index>/<int:card_index>')
@login_required
def show_answer(deck_index, card_index):
    card = decks[deck_index]['cards'][card_index]
    return render_template('show_answer.html', card=card)
 
@app.route('/quiz_complete')
@login_required
def quiz_complete():
    total_questions = session['current_card_index']
    correct_answers = session['correct_answers']
    incorrect_answers = session['incorrect_answers']
    unattempted_questions = session['unattempted_questions']
    user_id = session['user_id']
 
    # Update scores
    if user_id not in scores:
        scores[user_id] = {}
    deck_name = decks[session['deck_index']]['name']
    if deck_name not in scores[user_id]:
        scores[user_id][deck_name] = {'total_questions': 0, 'correct_answers': 0, 'incorrect_answers': 0, 'unattempted_questions': 0}
    scores[user_id][deck_name]['total_questions'] += total_questions
    scores[user_id][deck_name]['correct_answers'] += correct_answers
    scores[user_id][deck_name]['incorrect_answers'] += incorrect_answers
    scores[user_id][deck_name]['unattempted_questions'] += unattempted_questions
    save_data()
 
    return render_template('quiz_complete.html', total_questions=total_questions,
                           correct_answers=correct_answers, incorrect_answers=incorrect_answers,
                           unattempted_questions=unattempted_questions)

@app.route('/history')
@login_required
def history_page():
    user_id = session['user_id']
    user_history = history.get(user_id, {})
    return render_template('history.html', history=user_history, decks=decks)

@app.route('/history/deck/<int:deck_index>')
@login_required
def history_deck(deck_index):
    user_id = session['user_id']
    user_history = history.get(user_id, {}).get(deck_index, {})
    return render_template('history_deck.html', history=user_history, deck=decks[deck_index], deck_index=deck_index)

@app.route('/history/deck/<int:deck_index>/card/<int:card_index>')
@login_required
def history_card(deck_index, card_index):
    user_id = session['user_id']
    user_history = history.get(user_id, {}).get(deck_index, {}).get(card_index, [])
    return render_template('history_card.html', history=user_history, deck=decks[deck_index], card=decks[deck_index]['cards'][card_index], deck_index=deck_index)

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8000,debug=True)
