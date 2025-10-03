from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'taskflow-production-key-2024')

# In-memory storage for production demo
users_db = {}
tasks_db = {}
user_id_counter = 1
task_id_counter = 1

# Helper functions
def get_current_user():
    if 'user_id' in session:
        return users_db.get(session['user_id'])
    return None

def require_login():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return None

# Routes
@app.route('/')
def home():
    user = get_current_user()
    if user:
        # Get user's tasks
        user_tasks = [task for task in tasks_db.values() if task['user_id'] == user['id']]
        return render_template_string(DASHBOARD_TEMPLATE, user=user, tasks=user_tasks)
    return render_template_string(HOME_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        global user_id_counter
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        # Validation
        if not username or not email or not password:
            flash('All fields are required')
            return render_template_string(REGISTER_TEMPLATE)

        # Check if user exists
        for user in users_db.values():
            if user['username'] == username:
                flash('Username already exists')
                return render_template_string(REGISTER_TEMPLATE)
            if user['email'] == email:
                flash('Email already exists')
                return render_template_string(REGISTER_TEMPLATE)

        # Create user
        user = {
            'id': user_id_counter,
            'username': username,
            'email': email,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.now(),
            'is_admin': user_id_counter == 1  # First user is admin
        }
        users_db[user_id_counter] = user
        user_id_counter += 1

        # Log in user
        session['user_id'] = user['id']
        flash('Registration successful! Welcome to TaskFlow!')
        return redirect(url_for('home'))

    return render_template_string(REGISTER_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Find user
        user = None
        for u in users_db.values():
            if u['username'] == username:
                user = u
                break

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            flash(f'Welcome back, {user["username"]}!')
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')

    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out')
    return redirect(url_for('home'))

@app.route('/add_task', methods=['POST'])
def add_task():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    global task_id_counter
    user = get_current_user()

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority = request.form.get('priority', 'medium')
    category = request.form.get('category', 'general')

    if not title:
        flash('Task title is required')
        return redirect(url_for('home'))

    # Create task
    task = {
        'id': task_id_counter,
        'title': title,
        'description': description,
        'priority': priority,
        'category': category,
        'completed': False,
        'user_id': user['id'],
        'created_at': datetime.now(),
        'updated_at': datetime.now()
    }

    tasks_db[task_id_counter] = task
    task_id_counter += 1

    flash('Task added successfully!')
    return redirect(url_for('home'))

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    user = get_current_user()
    task = tasks_db.get(task_id)

    if task and task['user_id'] == user['id']:
        task['completed'] = not task['completed']
        task['updated_at'] = datetime.now()
        status = 'completed' if task['completed'] else 'reopened'
        flash(f'Task {status} successfully!')
    else:
        flash('Task not found or access denied')

    return redirect(url_for('home'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    user = get_current_user()
    task = tasks_db.get(task_id)

    if task and task['user_id'] == user['id']:
        del tasks_db[task_id]
        flash('Task deleted successfully!')
    else:
        flash('Task not found or access denied')

    return redirect(url_for('home'))

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    user = get_current_user()
    task = tasks_db.get(task_id)

    if not task or task['user_id'] != user['id']:
        flash('Task not found or access denied')
        return redirect(url_for('home'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'medium')
        category = request.form.get('category', 'general')

        if not title:
            flash('Task title is required')
        else:
            task['title'] = title
            task['description'] = description
            task['priority'] = priority
            task['category'] = category
            task['updated_at'] = datetime.now()
            flash('Task updated successfully!')
            return redirect(url_for('home'))

    return render_template_string(EDIT_TASK_TEMPLATE, task=task, user=user)

@app.route('/api/stats')
def api_stats():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    user_tasks = [task for task in tasks_db.values() if task['user_id'] == user['id']]
    completed_tasks = [task for task in user_tasks if task['completed']]
    pending_tasks = [task for task in user_tasks if not task['completed']]

    return jsonify({
        'total_tasks': len(user_tasks),
        'completed_tasks': len(completed_tasks),
        'pending_tasks': len(pending_tasks),
        'completion_rate': round(len(completed_tasks) / len(user_tasks) * 100, 1) if user_tasks else 0
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "online",
        "service": "TaskFlow",
        "version": "2.0",
        "users": len(users_db),
        "tasks": len(tasks_db)
    })

# Templates
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>TaskFlow - Professional Task Management</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            text-align: center;
            max-width: 500px;
            width: 100%;
            color: white;
        }
        h1 { font-size: 3em; margin-bottom: 10px; }
        .subtitle { font-size: 1.2em; margin-bottom: 30px; opacity: 0.9; }
        .btn {
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 15px 30px;
            border-radius: 50px;
            text-decoration: none;
            margin: 10px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            transition: all 0.3s ease;
            font-weight: 500;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        .features {
            margin-top: 40px;
            text-align: left;
            background: rgba(255, 255, 255, 0.05);
            padding: 25px;
            border-radius: 15px;
        }
        .features h3 { margin-bottom: 15px; text-align: center; }
        .features ul { list-style: none; }
        .features li { margin: 12px 0; padding-left: 25px; position: relative; }
        .features li:before { content: "✅"; position: absolute; left: 0; }
        .demo-note {
            background: rgba(76, 175, 80, 0.2);
            padding: 15px;
            border-radius: 10px;
            margin-top: 20px;
            border: 1px solid rgba(76, 175, 80, 0.3);
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 TaskFlow</h1>
        <p class="subtitle">Professional Task Management Platform</p>

        <div>
            <a href="/login" class="btn">Login</a>
            <a href="/register" class="btn">Register</a>
        </div>

        <div class="features">
            <h3>🎯 Features</h3>
            <ul>
                <li>User authentication & registration</li>
                <li>Create, edit & delete tasks</li>
                <li>Task priorities & categories</li>
                <li>Progress tracking & completion</li>
                <li>Beautiful responsive design</li>
                <li>Real-time statistics</li>
            </ul>
        </div>

        <div class="demo-note">
            <strong>🎉 Live Demo Ready!</strong><br>
            Register to create your account or use demo credentials:<br>
            <strong>Username:</strong> demo | <strong>Password:</strong> demo123
        </div>

        <p style="margin-top: 30px; opacity: 0.7; font-size: 0.9em;">
            🚀 TaskFlow by Mindscape Media • Production Deployment
        </p>
    </div>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Login - TaskFlow</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            width: 100%;
            max-width: 400px;
            color: white;
        }
        h2 { text-align: center; margin-bottom: 30px; font-size: 2em; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 500; }
        input {
            width: 100%;
            padding: 12px 15px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 16px;
        }
        input::placeholder { color: rgba(255, 255, 255, 0.7); }
        .btn {
            width: 100%;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-1px);
        }
        .links {
            text-align: center;
            margin-top: 25px;
        }
        .links a {
            color: rgba(255, 255, 255, 0.9);
            text-decoration: none;
            font-weight: 500;
        }
        .alert {
            background: rgba(255, 107, 107, 0.2);
            color: white;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 107, 107, 0.3);
        }
        .success {
            background: rgba(76, 175, 80, 0.2);
            border: 1px solid rgba(76, 175, 80, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Login to TaskFlow</h2>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert {% if 'Welcome' in message %}success{% endif %}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required placeholder="Enter your username">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required placeholder="Enter your password">
            </div>
            <button type="submit" class="btn">Login</button>
        </form>

        <div class="links">
            <a href="/register">Don't have an account? Register</a><br><br>
            <a href="/">← Back to Home</a>
        </div>
    </div>
</body>
</html>
'''

REGISTER_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Register - TaskFlow</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            width: 100%;
            max-width: 400px;
            color: white;
        }
        h2 { text-align: center; margin-bottom: 30px; font-size: 2em; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 500; }
        input {
            width: 100%;
            padding: 12px 15px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 16px;
        }
        input::placeholder { color: rgba(255, 255, 255, 0.7); }
        .btn {
            width: 100%;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-1px);
        }
        .links {
            text-align: center;
            margin-top: 25px;
        }
        .links a {
            color: rgba(255, 255, 255, 0.9);
            text-decoration: none;
            font-weight: 500;
        }
        .alert {
            background: rgba(255, 107, 107, 0.2);
            color: white;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 20px;
            border: 1px solid rgba(255, 107, 107, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Join TaskFlow</h2>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST">
            <div class="form-group">
                <label>Username</label>
                <input type="text" name="username" required placeholder="Choose a username">
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" required placeholder="your@email.com">
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required placeholder="Create a secure password">
            </div>
            <button type="submit" class="btn">Create Account</button>
        </form>

        <div class="links">
            <a href="/login">Already have an account? Login</a><br><br>
            <a href="/">← Back to Home</a>
        </div>
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - TaskFlow</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: white;
            flex-wrap: wrap;
        }
        .header h1 { font-size: 2.5em; }
        .user-info { text-align: right; }
        .add-task-form {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
        }
        .form-row {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
        }
        label {
            margin-bottom: 8px;
            font-weight: 500;
        }
        input, textarea, select {
            padding: 12px 15px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 16px;
        }
        input::placeholder, textarea::placeholder { color: rgba(255, 255, 255, 0.7); }
        .tasks-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .task-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
            transition: transform 0.3s ease;
        }
        .task-card:hover { transform: translateY(-5px); }
        .task-completed { opacity: 0.7; }
        .task-completed .task-title { text-decoration: line-through; }
        .task-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        .task-title {
            font-size: 1.3em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .task-desc {
            margin-bottom: 15px;
            opacity: 0.9;
            line-height: 1.5;
        }
        .task-meta {
            display: flex;
            justify-content: space-between;
            margin-bottom: 20px;
            font-size: 0.9em;
            opacity: 0.8;
        }
        .task-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 8px 16px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 8px;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 14px;
            font-weight: 500;
            white-space: nowrap;
        }
        .btn:hover { background: rgba(255, 255, 255, 0.3); }
        .btn-primary { background: rgba(76, 175, 80, 0.3); }
        .btn-danger { background: rgba(255, 107, 107, 0.3); }
        .btn-edit { background: rgba(255, 193, 7, 0.3); }
        .priority-high { border-left: 4px solid #ff6b6b; }
        .priority-medium { border-left: 4px solid #ffd93d; }
        .priority-low { border-left: 4px solid #6bcf7f; }
        .category-tag {
            background: rgba(255, 255, 255, 0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 500;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .stat-number {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .alert {
            background: rgba(76, 175, 80, 0.2);
            color: white;
            padding: 12px 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid rgba(76, 175, 80, 0.3);
        }
        .empty-state {
            text-align: center;
            padding: 40px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            color: white;
        }
        @media (max-width: 768px) {
            .header { flex-direction: column; text-align: center; gap: 15px; }
            .form-row { grid-template-columns: 1fr; }
            .tasks-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🚀 TaskFlow</h1>
                <p>Welcome back, {{ user.username }}! {% if user.is_admin %}(Admin){% endif %}</p>
            </div>
            <div class="user-info">
                <a href="/logout" class="btn btn-danger">Logout</a>
            </div>
        </div>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ tasks|length }}</div>
                <div>Total Tasks</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ tasks|selectattr('completed', 'equalto', False)|list|length }}</div>
                <div>Pending</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ tasks|selectattr('completed', 'equalto', True)|list|length }}</div>
                <div>Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{% if tasks %}{{ ((tasks|selectattr('completed', 'equalto', True)|list|length / tasks|length) * 100)|round(1) }}%{% else %}0%{% endif %}</div>
                <div>Progress</div>
            </div>
        </div>

        <div class="add-task-form">
            <h3 style="margin-bottom: 20px;">➕ Add New Task</h3>
            <form method="POST" action="/add_task">
                <div class="form-row">
                    <div class="form-group">
                        <label>Task Title</label>
                        <input type="text" name="title" required placeholder="What needs to be done?">
                    </div>
                    <div class="form-group">
                        <label>Priority</label>
                        <select name="priority">
                            <option value="low">🟢 Low</option>
                            <option value="medium" selected>🟡 Medium</option>
                            <option value="high">🔴 High</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Category</label>
                        <select name="category">
                            <option value="general">📋 General</option>
                            <option value="work">💼 Work</option>
                            <option value="personal">👤 Personal</option>
                            <option value="urgent">⚡ Urgent</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" rows="3" placeholder="Add more details about this task..."></textarea>
                </div>
                <button type="submit" class="btn btn-primary">Add Task</button>
            </form>
        </div>

        {% if tasks %}
        <div class="tasks-grid">
            {% for task in tasks|sort(attribute='created_at', reverse=true) %}
            <div class="task-card priority-{{ task.priority }} {% if task.completed %}task-completed{% endif %}">
                <div class="task-header">
                    <div class="task-title">
                        {% if task.completed %}✅{% else %}📋{% endif %}
                        {{ task.title }}
                    </div>
                    <div class="category-tag">{{ task.category }}</div>
                </div>

                {% if task.description %}
                <div class="task-desc">{{ task.description }}</div>
                {% endif %}

                <div class="task-meta">
                    <span>Priority: {{ task.priority.title() }}</span>
                    <span>{{ task.created_at.strftime('%m/%d/%Y') }}</span>
                </div>

                <div class="task-actions">
                    <a href="/complete_task/{{ task.id }}" class="btn {% if task.completed %}btn-edit{% else %}btn-primary{% endif %}">
                        {% if task.completed %}↩️ Reopen{% else %}✅ Complete{% endif %}
                    </a>
                    <a href="/edit_task/{{ task.id }}" class="btn btn-edit">✏️ Edit</a>
                    <a href="/delete_task/{{ task.id }}" class="btn btn-danger"
                       onclick="return confirm('Are you sure you want to delete this task?')">🗑️ Delete</a>
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty-state">
            <h3>🎯 Ready to be productive?</h3>
            <p>You don't have any tasks yet. Create your first task above to get started!</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

EDIT_TASK_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Edit Task - TaskFlow</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
        }
        .edit-form {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
        }
        h2 { text-align: center; margin-bottom: 30px; font-size: 2em; }
        .form-group { margin-bottom: 20px; }
        label { display: block; margin-bottom: 8px; font-weight: 500; }
        input, textarea, select {
            width: 100%;
            padding: 12px 15px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 16px;
        }
        input::placeholder, textarea::placeholder { color: rgba(255, 255, 255, 0.7); }
        .btn {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 15px 25px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 500;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            margin-right: 10px;
        }
        .btn:hover { background: rgba(255, 255, 255, 0.3); }
        .btn-primary { background: rgba(76, 175, 80, 0.3); }
        .actions { text-align: center; margin-top: 30px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="edit-form">
            <h2>✏️ Edit Task</h2>
            <form method="POST">
                <div class="form-group">
                    <label>Task Title</label>
                    <input type="text" name="title" value="{{ task.title }}" required>
                </div>
                <div class="form-group">
                    <label>Priority</label>
                    <select name="priority">
                        <option value="low" {% if task.priority == 'low' %}selected{% endif %}>🟢 Low</option>
                        <option value="medium" {% if task.priority == 'medium' %}selected{% endif %}>🟡 Medium</option>
                        <option value="high" {% if task.priority == 'high' %}selected{% endif %}>🔴 High</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Category</label>
                    <select name="category">
                        <option value="general" {% if task.category == 'general' %}selected{% endif %}>📋 General</option>
                        <option value="work" {% if task.category == 'work' %}selected{% endif %}>💼 Work</option>
                        <option value="personal" {% if task.category == 'personal' %}selected{% endif %}>👤 Personal</option>
                        <option value="urgent" {% if task.category == 'urgent' %}selected{% endif %}>⚡ Urgent</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" rows="4">{{ task.description or '' }}</textarea>
                </div>
                <div class="actions">
                    <button type="submit" class="btn btn-primary">💾 Save Changes</button>
                    <a href="/" class="btn">❌ Cancel</a>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
'''

# Create demo user on startup
if not users_db:
    demo_user = {
        'id': 1,
        'username': 'demo',
        'email': 'demo@taskflow.com',
        'password_hash': generate_password_hash('demo123'),
        'created_at': datetime.now(),
        'is_admin': True
    }
    users_db[1] = demo_user
    user_id_counter = 2

    # Add some demo tasks
    demo_tasks = [
        {
            'id': 1,
            'title': 'Welcome to TaskFlow!',
            'description': 'This is your first task. You can edit, complete, or delete it.',
            'priority': 'medium',
            'category': 'general',
            'completed': False,
            'user_id': 1,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        },
        {
            'id': 2,
            'title': 'Explore the features',
            'description': 'Try creating new tasks, changing priorities, and marking tasks complete.',
            'priority': 'low',
            'category': 'personal',
            'completed': False,
            'user_id': 1,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        },
        {
            'id': 3,
            'title': 'Complete your first task',
            'description': 'Click the checkmark to mark this task as completed!',
            'priority': 'high',
            'category': 'urgent',
            'completed': True,
            'user_id': 1,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
    ]

    for task in demo_tasks:
        tasks_db[task['id']] = task
    task_id_counter = 4

# Vercel entry point
application = app

if __name__ == '__main__':
    app.run(debug=True)