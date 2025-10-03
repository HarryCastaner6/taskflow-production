from flask import Flask, render_template_string, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import json
import random
import re

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'taskflow-production-key-2024')

# In-memory storage for production demo
users_db = {}
tasks_db = {}
boards_db = {}
activity_db = []
subtasks_db = {}
user_id_counter = 1
task_id_counter = 1
board_id_counter = 1
subtask_id_counter = 1

# Helper functions
def get_current_user():
    if 'user_id' in session:
        return users_db.get(session['user_id'])
    return None

def require_login():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return None

def add_activity(user_id, action, task_title=None, details=None, task_id=None):
    activity = {
        'id': len(activity_db) + 1,
        'user_id': user_id,
        'action': action,
        'task_title': task_title,
        'task_id': task_id,
        'details': details,
        'timestamp': datetime.now()
    }
    activity_db.insert(0, activity)  # Add to beginning for chronological order
    # Keep only last 100 activities
    if len(activity_db) > 100:
        activity_db.pop()

def get_gemini_suggestion(task_title, description=""):
    """Generate AI-powered task suggestions using simulated Gemini AI"""
    suggestions = [
        "Consider breaking this into smaller subtasks",
        "Add relevant tags for better organization",
        "Set priority based on urgency and importance",
        "Link to related documentation or resources",
        "Schedule regular check-ins for progress tracking",
        "Consider dependencies with other tasks",
        "Add time estimates for better planning",
        "Create a checklist for completion criteria"
    ]
    return random.choice(suggestions)

def auto_archive_completed_tasks():
    """Automatically archive tasks that have been in 'done' status for more than 7 days"""
    cutoff_date = datetime.now() - timedelta(days=7)
    for task in tasks_db.values():
        if (task['status'] == 'done' and
            task.get('completed_at') and
            task['completed_at'] < cutoff_date):
            task['status'] = 'archived'
            task['archived_at'] = datetime.now()
            add_activity(task['user_id'], 'Task auto-archived', task['title'], task_id=task['id'])

def get_task_subtasks(task_id):
    return [st for st in subtasks_db.values() if st['task_id'] == task_id]

def get_subtask_progress(task_id):
    subtasks = get_task_subtasks(task_id)
    if not subtasks:
        return 0, 0
    completed = len([st for st in subtasks if st['completed']])
    return completed, len(subtasks)

# Routes
@app.route('/')
def home():
    user = get_current_user()
    if user:
        return redirect(url_for('dashboard'))
    return render_template_string(HOME_TEMPLATE)

@app.route('/dashboard')
def dashboard():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    user = get_current_user()
    user_tasks = [task for task in tasks_db.values() if task['user_id'] == user['id']]
    user_boards = [board for board in boards_db.values() if user['id'] in board['members']]
    recent_activity = [activity for activity in activity_db if activity['user_id'] == user['id']][:10]

    # Task statistics
    todo_tasks = [t for t in user_tasks if t['status'] == 'todo']
    in_progress_tasks = [t for t in user_tasks if t['status'] == 'in_progress']
    done_tasks = [t for t in user_tasks if t['status'] == 'done']
    archived_tasks = [t for t in user_tasks if t['status'] == 'archived']

    stats = {
        'total': len(user_tasks),
        'todo': len(todo_tasks),
        'in_progress': len(in_progress_tasks),
        'done': len(done_tasks),
        'archived': len(archived_tasks),
        'completion_rate': round(len(done_tasks + archived_tasks) / len(user_tasks) * 100, 1) if user_tasks else 0
    }

    return render_template_string(DASHBOARD_TEMPLATE,
                                user=user,
                                boards=user_boards,
                                stats=stats,
                                recent_activity=recent_activity)

@app.route('/board/<int:board_id>')
def board_view(board_id):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    user = get_current_user()
    board = boards_db.get(board_id)

    if not board or user['id'] not in board['members']:
        flash('Board not found or access denied')
        return redirect(url_for('dashboard'))

    # Get tasks for this board
    board_tasks = [task for task in tasks_db.values() if task['board_id'] == board_id]

    # Organize tasks by status
    todo_tasks = [t for t in board_tasks if t['status'] == 'todo']
    in_progress_tasks = [t for t in board_tasks if t['status'] == 'in_progress']
    done_tasks = [t for t in board_tasks if t['status'] == 'done']

    # Add subtask progress to each task
    for task in board_tasks:
        completed, total = get_subtask_progress(task['id'])
        task['subtask_progress'] = {'completed': completed, 'total': total}
        task['subtasks'] = get_task_subtasks(task['id'])

    return render_template_string(BOARD_TEMPLATE,
                                user=user,
                                board=board,
                                todo_tasks=todo_tasks,
                                in_progress_tasks=in_progress_tasks,
                                done_tasks=done_tasks)

@app.route('/archive')
def archive():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    user = get_current_user()
    archived_tasks = [task for task in tasks_db.values()
                     if task['user_id'] == user['id'] and task['status'] == 'archived']

    # Sort by completion date (newest first)
    archived_tasks.sort(key=lambda x: x['completed_at'], reverse=True)

    # Add subtask progress
    for task in archived_tasks:
        completed, total = get_subtask_progress(task['id'])
        task['subtask_progress'] = {'completed': completed, 'total': total}

    return render_template_string(ARCHIVE_TEMPLATE, user=user, archived_tasks=archived_tasks)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        global user_id_counter, board_id_counter
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        full_name = request.form.get('full_name', '').strip()

        # Validation
        if not username or not email or not password or not full_name:
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
            'full_name': full_name,
            'password_hash': generate_password_hash(password),
            'created_at': datetime.now(),
            'is_admin': user_id_counter == 1
        }
        users_db[user_id_counter] = user

        # Create default board for new user
        default_board = {
            'id': board_id_counter,
            'name': f"{full_name}'s Board",
            'description': 'Your personal task board',
            'owner_id': user_id_counter,
            'members': [user_id_counter],
            'created_at': datetime.now()
        }
        boards_db[board_id_counter] = default_board
        board_id_counter += 1
        user_id_counter += 1

        # Log in user
        session['user_id'] = user['id']
        add_activity(user['id'], 'User registered', details=f'Welcome to TaskFlow!')
        flash('Registration successful! Welcome to TaskFlow!')
        return redirect(url_for('dashboard'))

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
            add_activity(user['id'], 'User logged in')
            flash(f'Welcome back, {user["full_name"]}!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password')

    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    user = get_current_user()
    if user:
        add_activity(user['id'], 'User logged out')
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
    tags = request.form.get('tags', '').strip()
    board_id = int(request.form.get('board_id', 1))

    if not title:
        flash('Task title is required')
        return redirect(request.referrer or url_for('dashboard'))

    # Process tags
    tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

    # Create task
    task = {
        'id': task_id_counter,
        'title': title,
        'description': description,
        'priority': priority,
        'category': category,
        'tags': tag_list,
        'status': 'todo',
        'board_id': board_id,
        'user_id': user['id'],
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'completed_at': None
    }

    tasks_db[task_id_counter] = task
    task_id_counter += 1

    add_activity(user['id'], 'Task created', task_title=title)
    flash('Task added successfully!')
    return redirect(request.referrer or url_for('dashboard'))

@app.route('/update_task_status/<int:task_id>/<status>')
def update_task_status(task_id, status):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    user = get_current_user()
    task = tasks_db.get(task_id)

    if task and task['user_id'] == user['id']:
        old_status = task['status']
        task['status'] = status
        task['updated_at'] = datetime.now()

        if status == 'done':
            task['completed_at'] = datetime.now()
            add_activity(user['id'], 'Task completed', task_title=task['title'])
        elif status == 'archived':
            task['completed_at'] = task['completed_at'] or datetime.now()
            add_activity(user['id'], 'Task archived', task_title=task['title'])
        else:
            add_activity(user['id'], f'Task moved to {status}', task_title=task['title'])

        flash(f'Task moved to {status.replace("_", " ").title()}!')
    else:
        flash('Task not found or access denied')

    return redirect(request.referrer or url_for('dashboard'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    user = get_current_user()
    task = tasks_db.get(task_id)

    if task and task['user_id'] == user['id']:
        # Delete associated subtasks
        task_subtasks = [st_id for st_id, st in subtasks_db.items() if st['task_id'] == task_id]
        for st_id in task_subtasks:
            del subtasks_db[st_id]

        add_activity(user['id'], 'Task deleted', task_title=task['title'])
        del tasks_db[task_id]
        flash('Task deleted successfully!')
    else:
        flash('Task not found or access denied')

    return redirect(request.referrer or url_for('dashboard'))

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    user = get_current_user()
    task = tasks_db.get(task_id)

    if not task or task['user_id'] != user['id']:
        flash('Task not found or access denied')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'medium')
        category = request.form.get('category', 'general')
        tags = request.form.get('tags', '').strip()

        if not title:
            flash('Task title is required')
        else:
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()] if tags else []

            task['title'] = title
            task['description'] = description
            task['priority'] = priority
            task['category'] = category
            task['tags'] = tag_list
            task['updated_at'] = datetime.now()

            add_activity(user['id'], 'Task updated', task_title=title)
            flash('Task updated successfully!')
            return redirect(request.referrer or url_for('dashboard'))

    # Get subtasks
    subtasks = get_task_subtasks(task_id)

    return render_template_string(EDIT_TASK_TEMPLATE, task=task, user=user, subtasks=subtasks)

@app.route('/add_subtask/<int:task_id>', methods=['POST'])
def add_subtask(task_id):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    global subtask_id_counter
    user = get_current_user()
    task = tasks_db.get(task_id)

    if not task or task['user_id'] != user['id']:
        flash('Task not found or access denied')
        return redirect(url_for('dashboard'))

    title = request.form.get('subtask_title', '').strip()
    if not title:
        flash('Subtask title is required')
        return redirect(request.referrer)

    subtask = {
        'id': subtask_id_counter,
        'task_id': task_id,
        'title': title,
        'completed': False,
        'created_at': datetime.now()
    }

    subtasks_db[subtask_id_counter] = subtask
    subtask_id_counter += 1

    add_activity(user['id'], 'Subtask added', task_title=task['title'], details=f'Added: {title}')
    flash('Subtask added successfully!')
    return redirect(request.referrer)

@app.route('/toggle_subtask/<int:subtask_id>')
def toggle_subtask(subtask_id):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    user = get_current_user()
    subtask = subtasks_db.get(subtask_id)

    if subtask:
        task = tasks_db.get(subtask['task_id'])
        if task and task['user_id'] == user['id']:
            subtask['completed'] = not subtask['completed']
            status = 'completed' if subtask['completed'] else 'reopened'
            add_activity(user['id'], f'Subtask {status}', task_title=task['title'], details=subtask['title'])
            flash(f'Subtask {status}!')

    return redirect(request.referrer)

@app.route('/create_board', methods=['POST'])
def create_board():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response

    global board_id_counter
    user = get_current_user()

    name = request.form.get('board_name', '').strip()
    description = request.form.get('board_description', '').strip()

    if not name:
        flash('Board name is required')
        return redirect(url_for('dashboard'))

    board = {
        'id': board_id_counter,
        'name': name,
        'description': description,
        'owner_id': user['id'],
        'members': [user['id']],
        'created_at': datetime.now()
    }

    boards_db[board_id_counter] = board
    board_id_counter += 1

    add_activity(user['id'], 'Board created', details=name)
    flash(f'Board "{name}" created successfully!')
    return redirect(url_for('dashboard'))

@app.route('/api/stats')
def api_stats():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Not authenticated'}), 401

    user_tasks = [task for task in tasks_db.values() if task['user_id'] == user['id']]

    stats = {
        'total_tasks': len(user_tasks),
        'todo_tasks': len([t for t in user_tasks if t['status'] == 'todo']),
        'in_progress_tasks': len([t for t in user_tasks if t['status'] == 'in_progress']),
        'done_tasks': len([t for t in user_tasks if t['status'] == 'done']),
        'archived_tasks': len([t for t in user_tasks if t['status'] == 'archived']),
        'completion_rate': round(len([t for t in user_tasks if t['status'] in ['done', 'archived']]) / len(user_tasks) * 100, 1) if user_tasks else 0
    }

    return jsonify(stats)

@app.route('/health')
def health():
    auto_archive_completed_tasks()  # Run auto-archiving on health checks
    return jsonify({
        "status": "online",
        "service": "TaskFlow Professional",
        "version": "4.0",
        "users": len(users_db),
        "tasks": len(tasks_db),
        "boards": len(boards_db)
    })

@app.route('/api/update_task_status', methods=['POST'])
def api_update_task_status():
    """API endpoint for drag-and-drop status updates"""
    redirect_response = require_login()
    if redirect_response:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json()
    task_id = data.get('task_id')
    new_status = data.get('status')

    user = get_current_user()
    task = tasks_db.get(int(task_id))

    if task and task['user_id'] == user['id']:
        old_status = task['status']
        task['status'] = new_status
        task['updated_at'] = datetime.now()

        if new_status == 'done':
            task['completed_at'] = datetime.now()
            add_activity(user['id'], 'Task completed', task['title'], task_id=task['id'])
        elif new_status == 'archived':
            task['completed_at'] = task['completed_at'] or datetime.now()
            task['archived_at'] = datetime.now()
            add_activity(user['id'], 'Task archived', task['title'], task_id=task['id'])
        else:
            add_activity(user['id'], f'Task moved to {new_status}', task['title'], task_id=task['id'])

        return jsonify({'success': True, 'message': f'Task moved to {new_status}'})

    return jsonify({'success': False, 'message': 'Task not found or access denied'}), 403

@app.route('/api/gemini_suggest', methods=['POST'])
def gemini_suggest():
    """API endpoint for Gemini AI task suggestions"""
    redirect_response = require_login()
    if redirect_response:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json()
    task_title = data.get('title', '')
    description = data.get('description', '')

    suggestion = get_gemini_suggestion(task_title, description)

    user = get_current_user()
    add_activity(user['id'], 'AI suggestion requested', task_title, details=f'Gemini: {suggestion}')

    return jsonify({'success': True, 'suggestion': suggestion})

@app.route('/api/quick_edit_task', methods=['POST'])
def quick_edit_task():
    """API endpoint for quick task editing"""
    redirect_response = require_login()
    if redirect_response:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json()
    task_id = int(data.get('task_id'))

    user = get_current_user()
    task = tasks_db.get(task_id)

    if task and task['user_id'] == user['id']:
        if 'title' in data:
            task['title'] = data['title']
        if 'description' in data:
            task['description'] = data['description']
        if 'priority' in data:
            task['priority'] = data['priority']
        if 'category' in data:
            task['category'] = data['category']
        if 'tags' in data:
            task['tags'] = [tag.strip() for tag in data['tags'].split(',') if tag.strip()]

        task['updated_at'] = datetime.now()
        add_activity(user['id'], 'Task updated', task['title'], task_id=task['id'])

        return jsonify({'success': True, 'message': 'Task updated successfully'})

    return jsonify({'success': False, 'message': 'Task not found or access denied'}), 403

# Templates
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>TaskFlow - Professional Task Board</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 60px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.2);
            text-align: center;
            max-width: 600px;
            width: 100%;
        }
        h1 {
            font-size: 3.5em;
            margin-bottom: 20px;
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }
        .subtitle {
            font-size: 1.4em;
            margin-bottom: 40px;
            color: #555;
            font-weight: 300;
        }
        .btn {
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 18px 36px;
            border-radius: 50px;
            text-decoration: none;
            margin: 12px;
            border: none;
            transition: all 0.3s ease;
            font-weight: 600;
            font-size: 16px;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }
        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
        }
        .features {
            margin-top: 50px;
            text-align: left;
            background: rgba(247, 250, 252, 0.8);
            padding: 35px;
            border-radius: 20px;
            border: 1px solid rgba(226, 232, 240, 0.8);
        }
        .features h3 {
            margin-bottom: 25px;
            text-align: center;
            color: #2d3748;
            font-size: 1.5em;
        }
        .features-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }
        .feature-item {
            display: flex;
            align-items: center;
            padding: 10px 0;
        }
        .feature-icon {
            font-size: 1.5em;
            margin-right: 12px;
            width: 30px;
        }
        .demo-note {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
            padding: 25px;
            border-radius: 16px;
            margin-top: 30px;
            box-shadow: 0 8px 25px rgba(79, 70, 229, 0.3);
        }
        @media (max-width: 768px) {
            .features-grid { grid-template-columns: 1fr; }
            .container { padding: 40px 30px; }
            h1 { font-size: 2.5em; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 TaskFlow</h1>
        <p class="subtitle">Professional Task Board & Project Management</p>

        <div>
            <a href="/login" class="btn">Sign In</a>
            <a href="/register" class="btn">Get Started</a>
        </div>

        <div class="features">
            <h3>🎯 Professional Features</h3>
            <div class="features-grid">
                <div class="feature-item">
                    <span class="feature-icon">📋</span>
                    <span>Kanban Board View</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">👥</span>
                    <span>Team Collaboration</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🎯</span>
                    <span>Task Priorities</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">📊</span>
                    <span>Progress Tracking</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">🏷️</span>
                    <span>Tags & Categories</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">📈</span>
                    <span>Analytics & Reports</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">⚡</span>
                    <span>Real-time Updates</span>
                </div>
                <div class="feature-item">
                    <span class="feature-icon">📱</span>
                    <span>Mobile Responsive</span>
                </div>
            </div>
        </div>

        <div class="demo-note">
            <strong>🎉 Try the Demo!</strong><br>
            Experience all features instantly:<br>
            <strong>Username:</strong> demo | <strong>Password:</strong> demo123
        </div>

        <p style="margin-top: 40px; color: #718096; font-size: 0.9em;">
            🚀 TaskFlow by Mindscape Media • Enterprise Ready
        </p>
    </div>
</body>
</html>
'''

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Sign In - TaskFlow</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 50px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.2);
            width: 100%;
            max-width: 450px;
        }
        h2 {
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5em;
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }
        .form-group { margin-bottom: 25px; }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #374151;
        }
        input {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            background: #f9fafb;
            color: #374151;
            font-size: 16px;
            transition: all 0.2s ease;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
            background: #fff;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        input::placeholder { color: #9ca3af; }
        .btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 18px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
        }
        .links {
            text-align: center;
            margin-top: 30px;
        }
        .links a {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s ease;
        }
        .links a:hover { color: #5a67d8; }
        .alert {
            background: #fef2f2;
            color: #dc2626;
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 25px;
            border: 1px solid #fecaca;
            font-size: 14px;
        }
        .success {
            background: #f0fdf4;
            color: #166534;
            border-color: #bbf7d0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Welcome Back</h2>

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
            <button type="submit" class="btn">Sign In</button>
        </form>

        <div class="links">
            <a href="/register">Don't have an account? Sign up</a><br><br>
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
    <title>Sign Up - TaskFlow</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .container {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 50px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
            border: 1px solid rgba(255, 255, 255, 0.2);
            width: 100%;
            max-width: 450px;
        }
        h2 {
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5em;
            background: linear-gradient(135deg, #1e3c72, #2a5298);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: 700;
        }
        .form-group { margin-bottom: 25px; }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #374151;
        }
        input {
            width: 100%;
            padding: 16px 20px;
            border: 2px solid #e5e7eb;
            border-radius: 12px;
            background: #f9fafb;
            color: #374151;
            font-size: 16px;
            transition: all 0.2s ease;
        }
        input:focus {
            outline: none;
            border-color: #667eea;
            background: #fff;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        input::placeholder { color: #9ca3af; }
        .btn {
            width: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 18px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
        }
        .links {
            text-align: center;
            margin-top: 30px;
        }
        .links a {
            color: #667eea;
            text-decoration: none;
            font-weight: 500;
            transition: color 0.2s ease;
        }
        .links a:hover { color: #5a67d8; }
        .alert {
            background: #fef2f2;
            color: #dc2626;
            padding: 16px;
            border-radius: 12px;
            margin-bottom: 25px;
            border: 1px solid #fecaca;
            font-size: 14px;
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
                <label>Full Name</label>
                <input type="text" name="full_name" required placeholder="Your full name">
            </div>
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
            <a href="/login">Already have an account? Sign in</a><br><br>
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
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f8fafc;
            min-height: 100vh;
        }

        /* Sidebar */
        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            width: 280px;
            height: 100vh;
            background: linear-gradient(180deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px 0;
            z-index: 1000;
            box-shadow: 4px 0 15px rgba(0, 0, 0, 0.1);
        }

        .sidebar-header {
            padding: 0 30px 30px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            margin-bottom: 30px;
        }

        .sidebar-header h1 {
            font-size: 1.8em;
            font-weight: 700;
            margin-bottom: 5px;
        }

        .sidebar-header p {
            opacity: 0.8;
            font-size: 0.9em;
        }

        .sidebar-menu {
            padding: 0 20px;
        }

        .menu-item {
            display: block;
            color: white;
            text-decoration: none;
            padding: 15px 20px;
            margin-bottom: 5px;
            border-radius: 12px;
            transition: all 0.2s ease;
            font-weight: 500;
        }

        .menu-item:hover, .menu-item.active {
            background: rgba(255, 255, 255, 0.15);
            transform: translateX(5px);
        }

        .menu-item i {
            margin-right: 12px;
            width: 20px;
        }

        /* Main Content */
        .main-content {
            margin-left: 280px;
            padding: 30px 40px;
        }

        .top-bar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
            background: white;
            padding: 20px 30px;
            border-radius: 16px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }

        .welcome-section h2 {
            font-size: 2em;
            color: #1a202c;
            margin-bottom: 5px;
        }

        .welcome-section p {
            color: #718096;
            font-size: 1.1em;
        }

        .user-actions {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }

        .stat-card {
            background: white;
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
            transition: transform 0.2s ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }

        .stat-number {
            font-size: 3em;
            font-weight: 700;
            margin-bottom: 10px;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .stat-label {
            color: #718096;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }

        /* Content Grid */
        .content-grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 30px;
        }

        .main-panel {
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }

        .side-panel {
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            height: fit-content;
        }

        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
        }

        .panel-header h3 {
            font-size: 1.5em;
            color: #1a202c;
            font-weight: 600;
        }

        /* Board Grid */
        .boards-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .board-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 16px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }

        .board-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 30px rgba(102, 126, 234, 0.4);
        }

        .board-card h4 {
            font-size: 1.3em;
            margin-bottom: 10px;
            font-weight: 600;
        }

        .board-card p {
            opacity: 0.9;
            margin-bottom: 15px;
            line-height: 1.5;
        }

        .board-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9em;
            opacity: 0.8;
        }

        /* Activity Feed */
        .activity-item {
            display: flex;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid #e2e8f0;
        }

        .activity-item:last-child {
            border-bottom: none;
        }

        .activity-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea, #764ba2);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 15px;
            color: white;
            font-size: 0.9em;
        }

        .activity-content {
            flex: 1;
        }

        .activity-text {
            font-weight: 500;
            color: #2d3748;
            margin-bottom: 3px;
        }

        .activity-time {
            font-size: 0.85em;
            color: #718096;
        }

        /* Buttons */
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }

        .btn-outline {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
            box-shadow: none;
        }

        .btn-outline:hover {
            background: #667eea;
            color: white;
        }

        .alert {
            background: #f0fdf4;
            color: #166534;
            padding: 15px 20px;
            border-radius: 12px;
            margin-bottom: 25px;
            border: 1px solid #bbf7d0;
            font-weight: 500;
        }

        /* Create Board Form */
        .create-board-form {
            margin-top: 20px;
            padding: 20px;
            background: #f7fafc;
            border-radius: 12px;
            border: 2px dashed #cbd5e0;
        }

        .form-group {
            margin-bottom: 15px;
        }

        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: 600;
            color: #374151;
        }

        .form-group input, .form-group textarea {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
        }

        .form-group input:focus, .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }

        @media (max-width: 1200px) {
            .content-grid { grid-template-columns: 1fr; }
        }

        @media (max-width: 768px) {
            .sidebar { transform: translateX(-100%); }
            .main-content { margin-left: 0; padding: 20px; }
            .top-bar { flex-direction: column; gap: 15px; text-align: center; }
            .stats-grid { grid-template-columns: repeat(2, 1fr); }
            .boards-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <!-- Sidebar -->
    <div class="sidebar">
        <div class="sidebar-header">
            <h1>🚀 TaskFlow</h1>
            <p>Project Management</p>
        </div>

        <nav class="sidebar-menu">
            <a href="/dashboard" class="menu-item active">
                <i>📊</i> Dashboard
            </a>
            <a href="#" class="menu-item">
                <i>📋</i> My Boards
            </a>
            <a href="/archive" class="menu-item">
                <i>📁</i> Archive
            </a>
            <a href="#" class="menu-item">
                <i>📈</i> Analytics
            </a>
            <a href="#" class="menu-item">
                <i>⚙️</i> Settings
            </a>
            <a href="/logout" class="menu-item">
                <i>🚪</i> Logout
            </a>
        </nav>
    </div>

    <!-- Main Content -->
    <div class="main-content">
        <!-- Top Bar -->
        <div class="top-bar">
            <div class="welcome-section">
                <h2>Welcome back, {{ user.full_name }}! 👋</h2>
                <p>Here's what's happening with your projects today.</p>
            </div>
            <div class="user-actions">
                <span style="color: #718096;">{{ user.username }}</span>
                {% if user.is_admin %}<span style="background: #ffd93d; color: #744210; padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: 600;">ADMIN</span>{% endif %}
            </div>
        </div>

        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total }}</div>
                <div class="stat-label">Total Tasks</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.todo }}</div>
                <div class="stat-label">To Do</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.in_progress }}</div>
                <div class="stat-label">In Progress</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.done }}</div>
                <div class="stat-label">Completed</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.completion_rate }}%</div>
                <div class="stat-label">Progress</div>
            </div>
        </div>

        <!-- Content Grid -->
        <div class="content-grid">
            <!-- Main Panel - Boards -->
            <div class="main-panel">
                <div class="panel-header">
                    <h3>My Boards</h3>
                    <button class="btn" onclick="toggleCreateForm()">+ New Board</button>
                </div>

                <div class="create-board-form" id="createForm" style="display: none;">
                    <form method="POST" action="/create_board">
                        <div class="form-group">
                            <label>Board Name</label>
                            <input type="text" name="board_name" required placeholder="Enter board name">
                        </div>
                        <div class="form-group">
                            <label>Description</label>
                            <textarea name="board_description" rows="3" placeholder="Describe your board..."></textarea>
                        </div>
                        <button type="submit" class="btn">Create Board</button>
                        <button type="button" class="btn btn-outline" onclick="toggleCreateForm()">Cancel</button>
                    </form>
                </div>

                <div class="boards-grid">
                    {% for board in boards %}
                    <div class="board-card" onclick="window.location.href='/board/{{ board.id }}'">
                        <h4>{{ board.name }}</h4>
                        <p>{{ board.description or 'No description' }}</p>
                        <div class="board-meta">
                            <span>{{ board.members|length }} member{{ 's' if board.members|length != 1 else '' }}</span>
                            <span>{{ board.created_at.strftime('%m/%d/%Y') }}</span>
                        </div>
                    </div>
                    {% endfor %}

                    {% if not boards %}
                    <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: #718096;">
                        <h4>No boards yet</h4>
                        <p>Create your first board to get started!</p>
                    </div>
                    {% endif %}
                </div>
            </div>

            <!-- Side Panel - Recent Activity -->
            <div class="side-panel">
                <div class="panel-header">
                    <h3>Recent Activity</h3>
                </div>

                <div class="activity-feed">
                    {% for activity in recent_activity %}
                    <div class="activity-item">
                        <div class="activity-icon">
                            {% if activity.action == 'Task created' %}🆕
                            {% elif activity.action == 'Task completed' %}✅
                            {% elif activity.action == 'Task updated' %}✏️
                            {% elif activity.action == 'Board created' %}📋
                            {% elif activity.action == 'User logged in' %}🔐
                            {% else %}📌{% endif %}
                        </div>
                        <div class="activity-content">
                            <div class="activity-text">
                                {{ activity.action }}
                                {% if activity.task_title %}: {{ activity.task_title }}{% endif %}
                                {% if activity.details %} - {{ activity.details }}{% endif %}
                            </div>
                            <div class="activity-time">{{ activity.timestamp.strftime('%I:%M %p') }}</div>
                        </div>
                    </div>
                    {% endfor %}

                    {% if not recent_activity %}
                    <div style="text-align: center; padding: 20px; color: #718096;">
                        <p>No recent activity</p>
                    </div>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>

    <script>
        function toggleCreateForm() {
            const form = document.getElementById('createForm');
            form.style.display = form.style.display === 'none' ? 'block' : 'none';
        }
    </script>
</body>
</html>
'''

BOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>{{ board.name }} - TaskFlow Professional</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 25%, #f093fb 50%, #f5576c 75%, #667eea 100%);
            background-size: 400% 400%;
            animation: gradientShift 15s ease infinite;
            min-height: 100vh;
            color: #1a202c;
        }

        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }

        /* Header */
        .header {
            background: white;
            padding: 20px 30px;
            border-bottom: 1px solid #e2e8f0;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
        }

        .header-content {
            display: flex;
            justify-content: space-between;
            align-items: center;
            max-width: 1400px;
            margin: 0 auto;
        }

        .board-info h1 {
            font-size: 2em;
            color: #1a202c;
            margin-bottom: 5px;
        }

        .board-info p {
            color: #718096;
        }

        .header-actions {
            display: flex;
            gap: 15px;
            align-items: center;
        }

        /* Board Container */
        .board-container {
            max-width: 1400px;
            margin: 30px auto;
            padding: 0 30px;
        }

        /* Kanban Board */
        .kanban-board {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 30px;
            margin-bottom: 30px;
        }

        .column {
            background: white;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
            min-height: 500px;
        }

        .column-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f1f5f9;
        }

        .column-title {
            font-size: 1.3em;
            font-weight: 700;
            color: #1a202c;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .task-count {
            background: #e2e8f0;
            color: #4a5568;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }

        .todo-column .column-title { color: #3182ce; }
        .todo-column .task-count { background: #e6fffa; color: #319795; }

        .progress-column .column-title { color: #d69e2e; }
        .progress-column .task-count { background: #fefcbf; color: #d69e2e; }

        .done-column .column-title { color: #38a169; }
        .done-column .task-count { background: #f0fff4; color: #38a169; }

        /* Task Cards */
        .task-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }

        .task-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
            border-color: #cbd5e0;
        }

        .task-card.priority-high {
            border-left: 4px solid #f56565;
        }

        .task-card.priority-medium {
            border-left: 4px solid #ed8936;
        }

        .task-card.priority-low {
            border-left: 4px solid #48bb78;
        }

        .task-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 12px;
        }

        .task-title {
            font-size: 1.1em;
            font-weight: 600;
            color: #2d3748;
            line-height: 1.3;
            flex: 1;
        }

        .task-priority {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.75em;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .priority-high {
            background: #fed7d7;
            color: #c53030;
        }

        .priority-medium {
            background: #feebc8;
            color: #dd6b20;
        }

        .priority-low {
            background: #c6f6d5;
            color: #276749;
        }

        .task-description {
            color: #718096;
            margin-bottom: 15px;
            line-height: 1.4;
            font-size: 0.95em;
        }

        .task-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 15px;
        }

        .tag {
            background: #edf2f7;
            color: #4a5568;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 500;
        }

        .task-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            font-size: 0.85em;
            color: #718096;
        }

        .category-badge {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: 500;
        }

        .subtask-progress {
            background: #f7fafc;
            border-radius: 8px;
            padding: 10px;
            margin-bottom: 15px;
        }

        .progress-bar {
            background: #e2e8f0;
            height: 6px;
            border-radius: 3px;
            margin-bottom: 8px;
            overflow: hidden;
        }

        .progress-fill {
            background: linear-gradient(135deg, #667eea, #764ba2);
            height: 100%;
            border-radius: 3px;
            transition: width 0.3s ease;
        }

        .progress-text {
            font-size: 0.8em;
            color: #4a5568;
            font-weight: 500;
        }

        .task-actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .task-btn {
            background: #f7fafc;
            color: #4a5568;
            border: 1px solid #e2e8f0;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.8em;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            text-decoration: none;
        }

        .task-btn:hover {
            background: #edf2f7;
            border-color: #cbd5e0;
        }

        .task-btn.move-btn { background: #e6fffa; color: #319795; border-color: #81e6d9; }
        .task-btn.edit-btn { background: #fefcbf; color: #d69e2e; border-color: #f6e05e; }
        .task-btn.delete-btn { background: #fed7d7; color: #e53e3e; border-color: #feb2b2; }

        /* Add Task Form */
        .add-task-form {
            background: #f8fafc;
            border: 2px dashed #cbd5e0;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 2fr 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
        }

        .form-group label {
            margin-bottom: 5px;
            font-weight: 600;
            color: #374151;
            font-size: 0.9em;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
            padding: 10px 12px;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.2s ease;
        }

        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }

        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }

        .btn-outline {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
        }

        .btn-outline:hover {
            background: #667eea;
            color: white;
        }

        .empty-column {
            text-align: center;
            padding: 40px 20px;
            color: #a0aec0;
            font-style: italic;
        }

        .alert {
            background: #f0fdf4;
            color: #166534;
            padding: 15px 20px;
            border-radius: 12px;
            margin-bottom: 25px;
            border: 1px solid #bbf7d0;
            font-weight: 500;
        }

        @media (max-width: 1200px) {
            .kanban-board { grid-template-columns: 1fr; }
            .form-grid { grid-template-columns: 1fr; }
        }

        @media (max-width: 768px) {
            .board-container { padding: 0 20px; }
            .header-content { flex-direction: column; gap: 15px; text-align: center; }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="header-content">
            <div class="board-info">
                <h1>{{ board.name }}</h1>
                <p>{{ board.description or 'No description' }}</p>
            </div>
            <div class="header-actions">
                <a href="/dashboard" class="btn btn-outline">← Dashboard</a>
                <a href="/archive" class="btn btn-outline">Archive</a>
            </div>
        </div>
    </div>

    <div class="board-container">
        {% with messages = get_flashed_messages() %}
            {% if messages %}
                {% for message in messages %}
                    <div class="alert">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Add Task Form -->
        <div class="add-task-form">
            <h3 style="margin-bottom: 20px; color: #2d3748;">➕ Add New Task</h3>
            <form method="POST" action="/add_task">
                <input type="hidden" name="board_id" value="{{ board.id }}">
                <div class="form-grid">
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
                <div class="form-group" style="margin-bottom: 15px;">
                    <label>Description</label>
                    <textarea name="description" rows="2" placeholder="Add more details about this task..."></textarea>
                </div>
                <div class="form-group" style="margin-bottom: 20px;">
                    <label>Tags (comma-separated)</label>
                    <input type="text" name="tags" placeholder="frontend, urgent, bug">
                </div>
                <button type="submit" class="btn">Add Task</button>
            </form>
        </div>

        <!-- Kanban Board -->
        <div class="kanban-board">
            <!-- To Do Column -->
            <div class="column todo-column">
                <div class="column-header">
                    <div class="column-title">
                        📋 To Do
                        <span class="task-count">{{ todo_tasks|length }}</span>
                    </div>
                </div>

                {% for task in todo_tasks %}
                <div class="task-card priority-{{ task.priority }}">
                    <div class="task-header">
                        <div class="task-title">{{ task.title }}</div>
                        <div class="task-priority priority-{{ task.priority }}">{{ task.priority }}</div>
                    </div>

                    {% if task.description %}
                    <div class="task-description">{{ task.description }}</div>
                    {% endif %}

                    {% if task.tags %}
                    <div class="task-tags">
                        {% for tag in task.tags %}
                        <span class="tag">#{{ tag }}</span>
                        {% endfor %}
                    </div>
                    {% endif %}

                    <div class="task-meta">
                        <span class="category-badge">{{ task.category }}</span>
                        <span>{{ task.updated_at.strftime('%m/%d %I:%M%p') }}</span>
                    </div>

                    {% if task.subtask_progress.total > 0 %}
                    <div class="subtask-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {{ (task.subtask_progress.completed / task.subtask_progress.total * 100)|round }}%"></div>
                        </div>
                        <div class="progress-text">{{ task.subtask_progress.completed }}/{{ task.subtask_progress.total }} subtasks completed</div>
                    </div>
                    {% endif %}

                    <div class="task-actions">
                        <a href="/update_task_status/{{ task.id }}/in_progress" class="task-btn move-btn">→ Start</a>
                        <a href="/edit_task/{{ task.id }}" class="task-btn edit-btn">✏️ Edit</a>
                        <a href="/delete_task/{{ task.id }}" class="task-btn delete-btn" onclick="return confirm('Delete this task?')">🗑️</a>
                    </div>
                </div>
                {% else %}
                <div class="empty-column">
                    No tasks in To Do
                </div>
                {% endfor %}
            </div>

            <!-- In Progress Column -->
            <div class="column progress-column">
                <div class="column-header">
                    <div class="column-title">
                        🔄 In Progress
                        <span class="task-count">{{ in_progress_tasks|length }}</span>
                    </div>
                </div>

                {% for task in in_progress_tasks %}
                <div class="task-card priority-{{ task.priority }}">
                    <div class="task-header">
                        <div class="task-title">{{ task.title }}</div>
                        <div class="task-priority priority-{{ task.priority }}">{{ task.priority }}</div>
                    </div>

                    {% if task.description %}
                    <div class="task-description">{{ task.description }}</div>
                    {% endif %}

                    {% if task.tags %}
                    <div class="task-tags">
                        {% for tag in task.tags %}
                        <span class="tag">#{{ tag }}</span>
                        {% endfor %}
                    </div>
                    {% endif %}

                    <div class="task-meta">
                        <span class="category-badge">{{ task.category }}</span>
                        <span>{{ task.updated_at.strftime('%m/%d %I:%M%p') }}</span>
                    </div>

                    {% if task.subtask_progress.total > 0 %}
                    <div class="subtask-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {{ (task.subtask_progress.completed / task.subtask_progress.total * 100)|round }}%"></div>
                        </div>
                        <div class="progress-text">{{ task.subtask_progress.completed }}/{{ task.subtask_progress.total }} subtasks completed</div>
                    </div>
                    {% endif %}

                    <div class="task-actions">
                        <a href="/update_task_status/{{ task.id }}/todo" class="task-btn">← Back</a>
                        <a href="/update_task_status/{{ task.id }}/done" class="task-btn move-btn">✅ Done</a>
                        <a href="/edit_task/{{ task.id }}" class="task-btn edit-btn">✏️ Edit</a>
                    </div>
                </div>
                {% else %}
                <div class="empty-column">
                    No tasks in progress
                </div>
                {% endfor %}
            </div>

            <!-- Done Column -->
            <div class="column done-column">
                <div class="column-header">
                    <div class="column-title">
                        ✅ Done
                        <span class="task-count">{{ done_tasks|length }}</span>
                    </div>
                </div>

                {% for task in done_tasks %}
                <div class="task-card priority-{{ task.priority }}" style="opacity: 0.8;">
                    <div class="task-header">
                        <div class="task-title" style="text-decoration: line-through;">{{ task.title }}</div>
                        <div class="task-priority priority-{{ task.priority }}">{{ task.priority }}</div>
                    </div>

                    {% if task.description %}
                    <div class="task-description">{{ task.description }}</div>
                    {% endif %}

                    {% if task.tags %}
                    <div class="task-tags">
                        {% for tag in task.tags %}
                        <span class="tag">#{{ tag }}</span>
                        {% endfor %}
                    </div>
                    {% endif %}

                    <div class="task-meta">
                        <span class="category-badge">{{ task.category }}</span>
                        <span>Completed {{ task.completed_at.strftime('%m/%d') if task.completed_at else task.updated_at.strftime('%m/%d') }}</span>
                    </div>

                    {% if task.subtask_progress.total > 0 %}
                    <div class="subtask-progress">
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {{ (task.subtask_progress.completed / task.subtask_progress.total * 100)|round }}%"></div>
                        </div>
                        <div class="progress-text">{{ task.subtask_progress.completed }}/{{ task.subtask_progress.total }} subtasks completed</div>
                    </div>
                    {% endif %}

                    <div class="task-actions">
                        <a href="/update_task_status/{{ task.id }}/in_progress" class="task-btn">↩️ Reopen</a>
                        <a href="/update_task_status/{{ task.id }}/archived" class="task-btn">📁 Archive</a>
                        <a href="/delete_task/{{ task.id }}" class="task-btn delete-btn" onclick="return confirm('Delete this task?')">🗑️</a>
                    </div>
                </div>
                {% else %}
                <div class="empty-column">
                    No completed tasks
                </div>
                {% endfor %}
            </div>
        </div>
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
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f8fafc;
            min-height: 100vh;
            padding: 30px 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
        }
        .edit-form {
            background: white;
            border-radius: 16px;
            padding: 40px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border: 1px solid #e2e8f0;
        }
        h2 {
            text-align: center;
            margin-bottom: 40px;
            font-size: 2.5em;
            color: #1a202c;
            font-weight: 700;
        }
        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-bottom: 25px;
        }
        .form-group { margin-bottom: 25px; }
        .form-group-full { grid-column: 1 / -1; }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #374151;
        }
        input, textarea, select {
            width: 100%;
            padding: 15px 18px;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            background: #f9fafb;
            color: #374151;
            font-size: 16px;
            transition: all 0.2s ease;
        }
        input:focus, textarea:focus, select:focus {
            outline: none;
            border-color: #667eea;
            background: #fff;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .subtasks-section {
            background: #f7fafc;
            border-radius: 12px;
            padding: 25px;
            margin-bottom: 25px;
            border: 1px solid #e2e8f0;
        }
        .subtasks-section h3 {
            margin-bottom: 20px;
            color: #2d3748;
            font-size: 1.3em;
        }
        .subtask-item {
            display: flex;
            align-items: center;
            padding: 12px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        .subtask-item:last-child { border-bottom: none; }
        .subtask-checkbox {
            margin-right: 12px;
            transform: scale(1.2);
        }
        .subtask-text {
            flex: 1;
            font-weight: 500;
            color: #2d3748;
        }
        .subtask-text.completed {
            text-decoration: line-through;
            opacity: 0.6;
        }
        .add-subtask-form {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .add-subtask-form input {
            flex: 1;
            margin-bottom: 0;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            font-size: 16px;
            font-weight: 600;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
            margin-right: 15px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4);
        }
        .btn-outline {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
            box-shadow: none;
        }
        .btn-outline:hover {
            background: #667eea;
            color: white;
        }
        .btn-small {
            padding: 8px 16px;
            font-size: 14px;
            margin-right: 0;
        }
        .actions {
            text-align: center;
            margin-top: 40px;
            padding-top: 30px;
            border-top: 1px solid #e2e8f0;
        }
        @media (max-width: 768px) {
            .form-grid { grid-template-columns: 1fr; }
            .edit-form { padding: 30px 25px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="edit-form">
            <h2>✏️ Edit Task</h2>
            <form method="POST">
                <div class="form-grid">
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
                        <label>Tags (comma-separated)</label>
                        <input type="text" name="tags" value="{{ task.tags|join(', ') if task.tags else '' }}" placeholder="frontend, urgent, bug">
                    </div>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea name="description" rows="4">{{ task.description or '' }}</textarea>
                </div>

                <!-- Subtasks Section -->
                <div class="subtasks-section">
                    <h3>📝 Subtasks</h3>
                    {% if subtasks %}
                        {% for subtask in subtasks %}
                        <div class="subtask-item">
                            <input type="checkbox" class="subtask-checkbox"
                                   {% if subtask.completed %}checked{% endif %}
                                   onchange="window.location.href='/toggle_subtask/{{ subtask.id }}'">
                            <span class="subtask-text {% if subtask.completed %}completed{% endif %}">
                                {{ subtask.title }}
                            </span>
                        </div>
                        {% endfor %}
                    {% else %}
                        <p style="color: #718096; font-style: italic;">No subtasks yet</p>
                    {% endif %}

                    <form method="POST" action="/add_subtask/{{ task.id }}" class="add-subtask-form">
                        <input type="text" name="subtask_title" placeholder="Add a subtask..." required>
                        <button type="submit" class="btn btn-small">Add</button>
                    </form>
                </div>

                <div class="actions">
                    <button type="submit" class="btn">💾 Save Changes</button>
                    <a href="javascript:history.back()" class="btn btn-outline">❌ Cancel</a>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
'''

ARCHIVE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Archive - TaskFlow</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: #f8fafc;
            min-height: 100vh;
            padding: 30px 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 2.5em;
            color: #1a202c;
            font-weight: 700;
        }
        .header p {
            color: #718096;
            margin-top: 5px;
        }
        .archive-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }
        .task-card {
            background: white;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
            opacity: 0.9;
            transition: all 0.2s ease;
        }
        .task-card:hover {
            opacity: 1;
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }
        .task-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }
        .task-title {
            font-size: 1.3em;
            font-weight: 600;
            color: #2d3748;
            text-decoration: line-through;
            opacity: 0.8;
        }
        .archived-badge {
            background: #e2e8f0;
            color: #4a5568;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
        }
        .task-description {
            color: #718096;
            margin-bottom: 15px;
            line-height: 1.5;
        }
        .task-meta {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            font-size: 0.9em;
            color: #718096;
        }
        .category-badge {
            background: #f7fafc;
            color: #4a5568;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8em;
        }
        .progress-section {
            background: #f7fafc;
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 15px;
        }
        .progress-bar {
            background: #e2e8f0;
            height: 6px;
            border-radius: 3px;
            margin-bottom: 8px;
            overflow: hidden;
        }
        .progress-fill {
            background: #48bb78;
            height: 100%;
            border-radius: 3px;
        }
        .progress-text {
            font-size: 0.8em;
            color: #4a5568;
            font-weight: 500;
        }
        .btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 600;
            text-decoration: none;
            display: inline-block;
            transition: all 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        }
        .btn-outline {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
        }
        .btn-outline:hover {
            background: #667eea;
            color: white;
        }
        .empty-state {
            text-align: center;
            padding: 60px 20px;
            background: white;
            border-radius: 16px;
            color: #718096;
        }
        .empty-state h3 {
            font-size: 1.5em;
            margin-bottom: 10px;
        }
        @media (max-width: 768px) {
            .header { flex-direction: column; gap: 15px; text-align: center; }
            .archive-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>📁 Task Archive</h1>
                <p>Completed and archived tasks - {{ archived_tasks|length }} total</p>
            </div>
            <div>
                <a href="/dashboard" class="btn btn-outline">← Dashboard</a>
            </div>
        </div>

        {% if archived_tasks %}
        <div class="archive-grid">
            {% for task in archived_tasks %}
            <div class="task-card">
                <div class="task-header">
                    <div class="task-title">{{ task.title }}</div>
                    <span class="archived-badge">ARCHIVED</span>
                </div>

                {% if task.description %}
                <div class="task-description">{{ task.description }}</div>
                {% endif %}

                <div class="task-meta">
                    <span class="category-badge">{{ task.category }}</span>
                    <span>Completed {{ task.completed_at.strftime('%m/%d/%Y') if task.completed_at else 'Unknown' }}</span>
                </div>

                {% if task.subtask_progress.total > 0 %}
                <div class="progress-section">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {{ (task.subtask_progress.completed / task.subtask_progress.total * 100)|round }}%"></div>
                    </div>
                    <div class="progress-text">{{ task.subtask_progress.completed }}/{{ task.subtask_progress.total }} subtasks completed</div>
                </div>
                {% endif %}

                <div style="font-size: 0.85em; color: #a0aec0;">
                    Priority: {{ task.priority.title() }} |
                    Created: {{ task.created_at.strftime('%m/%d/%Y') }}
                </div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <div class="empty-state">
            <h3>🗂️ No archived tasks yet</h3>
            <p>Completed tasks that are archived will appear here</p>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''

# Initialize counters for production
if not users_db:
    user_id_counter = 1
    board_id_counter = 1
    task_id_counter = 1
    subtask_id_counter = 1

# Vercel entry point
application = app

if __name__ == '__main__':
    app.run(debug=True)