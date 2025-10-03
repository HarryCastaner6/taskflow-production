import os
import sys
from pathlib import Path

# Add the root directory to Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from flask import Flask, render_template_string, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'taskflow-production-key-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Task Model
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    completed = db.Column(db.Boolean, default=False)
    priority = db.Column(db.String(10), default='medium')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def home():
    if current_user.is_authenticated:
        tasks = Task.query.filter_by(user_id=current_user.id).all()
        return render_template_string(DASHBOARD_TEMPLATE, tasks=tasks, user=current_user)
    return render_template_string(HOME_TEMPLATE)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('home'))
        flash('Invalid username or password')

    return render_template_string(LOGIN_TEMPLATE)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
        elif User.query.filter_by(email=email).first():
            flash('Email already exists')
        else:
            user = User(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for('home'))

    return render_template_string(REGISTER_TEMPLATE)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/add_task', methods=['POST'])
@login_required
def add_task():
    title = request.form.get('title')
    description = request.form.get('description')
    priority = request.form.get('priority', 'medium')

    if title:
        task = Task(title=title, description=description, priority=priority, user_id=current_user.id)
        db.session.add(task)
        db.session.commit()
        flash('Task added successfully!')

    return redirect(url_for('home'))

@app.route('/complete_task/<int:task_id>')
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == current_user.id:
        task.completed = not task.completed
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for('home'))

@app.route('/api/health')
def health():
    return jsonify({
        "status": "online",
        "service": "TaskFlow",
        "version": "2.0",
        "users": User.query.count(),
        "tasks": Task.query.count()
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
            width: 90%;
        }
        h1 { color: white; margin-bottom: 20px; font-size: 2.5em; }
        p { color: rgba(255, 255, 255, 0.9); margin-bottom: 30px; font-size: 1.1em; }
        .btn {
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 12px 30px;
            border-radius: 50px;
            text-decoration: none;
            margin: 10px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            transition: all 0.3s ease;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        }
        .features {
            margin-top: 30px;
            text-align: left;
            color: rgba(255, 255, 255, 0.8);
        }
        .features ul { list-style: none; }
        .features li { margin: 10px 0; padding-left: 20px; position: relative; }
        .features li:before { content: "✅"; position: absolute; left: 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 TaskFlow</h1>
        <p>Professional Task Management Platform</p>
        <p>Successfully deployed and running on Vercel!</p>

        <a href="/login" class="btn">Login</a>
        <a href="/register" class="btn">Register</a>

        <div class="features">
            <h3>Features:</h3>
            <ul>
                <li>User Authentication</li>
                <li>Task Management</li>
                <li>Real-time Updates</li>
                <li>Mobile Responsive</li>
                <li>Glass Morphism Design</li>
            </ul>
        </div>

        <p style="margin-top: 30px; font-size: 0.9em;">
            <strong>Demo Credentials:</strong><br>
            Username: admin | Password: admin123
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
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            width: 90%;
            max-width: 400px;
        }
        h2 { color: white; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { color: white; display: block; margin-bottom: 5px; }
        input {
            width: 100%;
            padding: 12px;
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
            padding: 12px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-1px);
        }
        .link {
            text-align: center;
            margin-top: 20px;
        }
        .link a {
            color: rgba(255, 255, 255, 0.9);
            text-decoration: none;
        }
        .alert { color: #ff6b6b; margin-bottom: 15px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Login to TaskFlow</h2>
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
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn">Login</button>
        </form>
        <div class="link">
            <a href="/register">Don't have an account? Register</a><br>
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
        }
        .container {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 40px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            width: 90%;
            max-width: 400px;
        }
        h2 { color: white; text-align: center; margin-bottom: 30px; }
        .form-group { margin-bottom: 20px; }
        label { color: white; display: block; margin-bottom: 5px; }
        input {
            width: 100%;
            padding: 12px;
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
            padding: 12px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s ease;
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-1px);
        }
        .link {
            text-align: center;
            margin-top: 20px;
        }
        .link a {
            color: rgba(255, 255, 255, 0.9);
            text-decoration: none;
        }
        .alert { color: #ff6b6b; margin-bottom: 15px; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Register for TaskFlow</h2>
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
                <input type="text" name="username" required>
            </div>
            <div class="form-group">
                <label>Email</label>
                <input type="email" name="email" required>
            </div>
            <div class="form-group">
                <label>Password</label>
                <input type="password" name="password" required>
            </div>
            <button type="submit" class="btn">Register</button>
        </form>
        <div class="link">
            <a href="/login">Already have an account? Login</a><br>
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
        .header {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            display: flex;
            justify-content: space-between;
            align-items: center;
            color: white;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .add-task {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        .tasks-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .task-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
            transition: transform 0.3s ease;
        }
        .task-card:hover { transform: translateY(-5px); }
        .task-completed { opacity: 0.6; }
        .task-title { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }
        .task-desc { margin-bottom: 15px; opacity: 0.9; }
        .task-actions { display: flex; gap: 10px; }
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
        }
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
        }
        .btn-danger { background: rgba(255, 107, 107, 0.3); }
        .btn-success { background: rgba(76, 175, 80, 0.3); }
        .form-row { display: flex; gap: 15px; margin-bottom: 15px; }
        .form-group { flex: 1; }
        label { color: white; display: block; margin-bottom: 5px; }
        input, textarea, select {
            width: 100%;
            padding: 12px;
            border: 1px solid rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.1);
            color: white;
            font-size: 16px;
        }
        input::placeholder, textarea::placeholder { color: rgba(255, 255, 255, 0.7); }
        .priority-high { border-left: 4px solid #ff6b6b; }
        .priority-medium { border-left: 4px solid #ffd93d; }
        .priority-low { border-left: 4px solid #6bcf7f; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 TaskFlow Dashboard</h1>
            <div>
                Welcome, {{ user.username }}!
                <a href="/logout" class="btn" style="margin-left: 15px;">Logout</a>
            </div>
        </div>

        <div class="add-task">
            <h3 style="color: white; margin-bottom: 20px;">Add New Task</h3>
            <form method="POST" action="/add_task">
                <div class="form-row">
                    <div class="form-group">
                        <label>Task Title</label>
                        <input type="text" name="title" required placeholder="Enter task title...">
                    </div>
                    <div class="form-group">
                        <label>Priority</label>
                        <select name="priority">
                            <option value="low">Low</option>
                            <option value="medium" selected>Medium</option>
                            <option value="high">High</option>
                        </select>
                    </div>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" rows="3" placeholder="Enter task description..."></textarea>
                </div>
                <button type="submit" class="btn">Add Task</button>
            </form>
        </div>

        <div class="tasks-grid">
            {% for task in tasks %}
            <div class="task-card priority-{{ task.priority }} {% if task.completed %}task-completed{% endif %}">
                <div class="task-title">
                    {% if task.completed %}✅{% else %}📋{% endif %}
                    {{ task.title }}
                </div>
                {% if task.description %}
                <div class="task-desc">{{ task.description }}</div>
                {% endif %}
                <div style="margin-bottom: 15px;">
                    <small style="opacity: 0.7;">
                        Priority: {{ task.priority.title() }} |
                        Created: {{ task.created_at.strftime('%m/%d/%Y') }}
                    </small>
                </div>
                <div class="task-actions">
                    <a href="/complete_task/{{ task.id }}"
                       class="btn {% if task.completed %}btn-success{% endif %}">
                        {% if task.completed %}Mark Incomplete{% else %}Mark Complete{% endif %}
                    </a>
                    <a href="/delete_task/{{ task.id }}"
                       class="btn btn-danger"
                       onclick="return confirm('Delete this task?')">Delete</a>
                </div>
            </div>
            {% endfor %}

            {% if tasks|length == 0 %}
            <div class="task-card">
                <div class="task-title">No tasks yet!</div>
                <div class="task-desc">Create your first task using the form above.</div>
            </div>
            {% endif %}
        </div>
    </div>
</body>
</html>
'''

# Initialize database and create admin user
with app.app_context():
    db.create_all()

    # Create admin user if not exists
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', email='admin@taskflow.com', is_admin=True)
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

# Vercel WSGI application
application = app