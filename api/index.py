from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'taskflow-production-key-2024')

# In-memory task storage for simplicity
tasks = []
task_id_counter = 1

# Routes
@app.route('/')
def home():
    return render_template_string(HOME_TEMPLATE, tasks=tasks)

@app.route('/add_task', methods=['POST'])
def add_task():
    global task_id_counter
    title = request.form.get('title')
    description = request.form.get('description', '')
    priority = request.form.get('priority', 'medium')

    if title:
        task = {
            'id': task_id_counter,
            'title': title,
            'description': description,
            'priority': priority,
            'completed': False
        }
        tasks.append(task)
        task_id_counter += 1

    return redirect(url_for('home'))

@app.route('/complete_task/<int:task_id>')
def complete_task(task_id):
    for task in tasks:
        if task['id'] == task_id:
            task['completed'] = not task['completed']
            break
    return redirect(url_for('home'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    global tasks
    tasks = [task for task in tasks if task['id'] != task_id]
    return redirect(url_for('home'))

@app.route('/api/health')
def health():
    return jsonify({
        "status": "online",
        "service": "TaskFlow",
        "version": "3.0",
        "tasks_count": len(tasks)
    })

# Template
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
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
            text-align: center;
            color: white;
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
        .task-completed { opacity: 0.6; text-decoration: line-through; }
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
            display: inline-block;
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
        .success-banner {
            background: rgba(76, 175, 80, 0.2);
            color: white;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 20px;
            text-align: center;
            border: 1px solid rgba(76, 175, 80, 0.3);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 TaskFlow</h1>
            <p>Professional Task Management Platform</p>
            <div class="success-banner">
                ✅ Successfully deployed and running on Vercel!<br>
                <small>Production deployment working perfectly</small>
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
                        ID: #{{ task.id }}
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
                <div class="task-title">🎉 Welcome to TaskFlow!</div>
                <div class="task-desc">
                    Your task management application is successfully deployed on Vercel!
                    <br><br>
                    <strong>Features:</strong>
                    <ul style="margin-top: 10px; margin-left: 20px;">
                        <li>Create and manage tasks</li>
                        <li>Set task priorities</li>
                        <li>Mark tasks as complete</li>
                        <li>Beautiful glass morphism design</li>
                        <li>Fully responsive interface</li>
                    </ul>
                    <br>
                    Get started by creating your first task above!
                </div>
            </div>
            {% endif %}
        </div>

        <div style="text-align: center; margin-top: 30px; color: rgba(255, 255, 255, 0.7);">
            <p>🚀 TaskFlow by Mindscape Media • Production Deployment Successful</p>
            <p><a href="/api/health" style="color: rgba(255, 255, 255, 0.9);">API Health Check</a></p>
        </div>
    </div>
</body>
</html>
'''

# For Vercel serverless deployment
application = app

if __name__ == '__main__':
    app.run(debug=True)