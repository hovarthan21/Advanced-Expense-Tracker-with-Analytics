from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import json
import os
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='.', static_folder='.')
app.secret_key = 'expense_tracker_secret_key_2024'
CORS(app)

DATA_FILE = 'users.json'

def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(DATA_FILE, 'w') as f:
        json.dump(users, f, indent=2)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    users = load_users()
    
    if username in users:
        return jsonify({'success': False, 'message': 'Username already exists'})
    
    users[username] = {
        'username': username,
        'password': password,
        'transactions': [],
        'settings': {
            'currency': '$',
            'dateFormat': 'mm/dd/yyyy'
        }
    }
    
    save_users(users)
    return jsonify({'success': True, 'message': 'Registration successful'})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    users = load_users()
    
    if username in users and users[username]['password'] == password:
        session['username'] = username
        return jsonify({'success': True, 'message': 'Login successful'})
    
    return jsonify({'success': False, 'message': 'Invalid credentials'})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({'success': True, 'message': 'Logout successful'})

@app.route('/api/transactions', methods=['GET'])
def get_transactions():
    username = session.get('username')
    if not username:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    users = load_users()
    user_data = users.get(username, {})
    
   
    time_filter = request.args.get('filter', 'all')
    transactions = user_data.get('transactions', [])
    
    if time_filter != 'all':
        now = datetime.now()
        if time_filter == 'daily':
            target_date = now.strftime('%Y-%m-%d')
            transactions = [t for t in transactions if t['date'] == target_date]
        elif time_filter == 'weekly':
            week_ago = now - timedelta(days=7)
            transactions = [t for t in transactions if datetime.strptime(t['date'], '%Y-%m-%d') >= week_ago]
        elif time_filter == 'monthly':
            month_ago = now - timedelta(days=30)
            transactions = [t for t in transactions if datetime.strptime(t['date'], '%Y-%m-%d') >= month_ago]
    
    return jsonify({'success': True, 'transactions': transactions})

@app.route('/api/transactions', methods=['POST'])
def add_transaction():
    username = session.get('username')
    if not username:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    data = request.json
    transaction = {
        'id': data.get('id'),
        'type': data.get('type'),
        'category': data.get('category'),
        'amount': float(data.get('amount')),
        'description': data.get('description'),
        'date': data.get('date'),
        'day': data.get('day')
    }
    
    users = load_users()
    if username in users:
        users[username]['transactions'].append(transaction)
        save_users(users)
        return jsonify({'success': True, 'message': 'Transaction added'})
    
    return jsonify({'success': False, 'message': 'User not found'})

@app.route('/api/transactions/<int:transaction_id>', methods=['DELETE'])
def delete_transaction(transaction_id):
    username = session.get('username')
    if not username:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    users = load_users()
    if username in users:
        user_transactions = users[username]['transactions']
        users[username]['transactions'] = [t for t in user_transactions if t['id'] != transaction_id]
        save_users(users)
        return jsonify({'success': True, 'message': 'Transaction deleted'})
    
    return jsonify({'success': False, 'message': 'User not found'})

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard():
    username = session.get('username')
    if not username:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    users = load_users()
    user_data = users.get(username, {})
    transactions = user_data.get('transactions', [])
    
    
    total_spent = sum(t['amount'] for t in transactions if t['type'] == 'spent')
    total_received = sum(t['amount'] for t in transactions if t['type'] == 'received')
    
    spent_categories = {}
    received_categories = {}
    
    for transaction in transactions:
        if transaction['type'] == 'spent':
            spent_categories[transaction['category']] = spent_categories.get(transaction['category'], 0) + transaction['amount']
        else:
            received_categories[transaction['category']] = received_categories.get(transaction['category'], 0) + transaction['amount']
    
    return jsonify({
        'success': True,
        'total_spent': total_spent,
        'total_received': total_received,
        'spent_breakdown': spent_categories,
        'received_breakdown': received_categories
    })

@app.route('/api/settings', methods=['POST'])
def save_settings():
    username = session.get('username')
    if not username:
        return jsonify({'success': False, 'message': 'Not authenticated'})
    
    data = request.json
    users = load_users()
    
    if username in users:
        users[username]['settings'] = data
        save_users(users)
        return jsonify({'success': True, 'message': 'Settings saved'})
    
    return jsonify({'success': False, 'message': 'User not found'})

if __name__ == '__main__':

    app.run(debug=True, port=5000)
