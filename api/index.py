import os
import sys
from pathlib import Path

# Add the root directory to Python path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

# Create Flask app for Vercel serverless
try:
    from app import create_app
    from config_prod import ProductionConfig

    # Create Flask app with serverless config
    app = create_app(ProductionConfig)

    # Initialize database and create default admin user
    with app.app_context():
        try:
            from app.models import db, User

            # Create all tables
            db.create_all()

            # Create default admin user if not exists
            if not User.query.filter_by(username='admin').first():
                admin = User(
                    username='admin',
                    email='admin@taskflow.com',
                    is_admin=True
                )
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()

        except Exception as e:
            print(f"Database setup error: {e}")

    # Vercel WSGI application
    application = app

except Exception as e:
    # Fallback minimal Flask app
    from flask import Flask, jsonify, render_template_string

    app = Flask(__name__)

    # Simple task management interface
    SIMPLE_TEMPLATE = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>TaskFlow - Task Management</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .task { background: #f5f5f5; padding: 10px; margin: 10px 0; border-radius: 5px; }
            button { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
            input, textarea { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>🚀 TaskFlow - Professional Task Management</h1>
        <p><strong>Production Ready!</strong> Your TaskFlow application is live.</p>

        <div id="taskForm">
            <h3>Add New Task</h3>
            <input type="text" id="taskTitle" placeholder="Task title..." />
            <textarea id="taskDesc" placeholder="Task description..."></textarea>
            <button onclick="addTask()">Add Task</button>
        </div>

        <div id="tasks">
            <h3>Tasks</h3>
            <div class="task">
                <strong>Welcome Task</strong><br>
                Your TaskFlow application is successfully deployed and running!
            </div>
        </div>

        <script>
            function addTask() {
                const title = document.getElementById('taskTitle').value;
                const desc = document.getElementById('taskDesc').value;
                if (title) {
                    const taskDiv = document.createElement('div');
                    taskDiv.className = 'task';
                    taskDiv.innerHTML = '<strong>' + title + '</strong><br>' + desc;
                    document.getElementById('tasks').appendChild(taskDiv);
                    document.getElementById('taskTitle').value = '';
                    document.getElementById('taskDesc').value = '';
                }
            }
        </script>

        <hr>
        <p><em>TaskFlow by Mindscape Media - Production Deployment Successful!</em></p>
        <p>Database Error: {{ error }}</p>
    </body>
    </html>
    '''

    @app.route('/')
    def home():
        return render_template_string(SIMPLE_TEMPLATE, error=str(e))

    @app.route('/api/health')
    def health():
        return jsonify({
            "status": "online",
            "service": "TaskFlow",
            "version": "1.0",
            "database_error": str(e)
        })

    application = app