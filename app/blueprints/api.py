from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Task, Tag
from datetime import datetime

api_bp = Blueprint('api', __name__)

@api_bp.route('/tasks', methods=['GET'])
@login_required
def get_tasks():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return jsonify([task.to_dict() for task in tasks])

@api_bp.route('/tasks/<int:task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    return jsonify(task.to_dict())

@api_bp.route('/tasks', methods=['POST'])
@login_required
def create_task():
    data = request.json
    task = Task(
        title=data.get('title'),
        description=data.get('description'),
        due_date=datetime.fromisoformat(data['due_date']) if data.get('due_date') else None,
        priority=data.get('priority', 'medium'),
        status=data.get('status', 'pending'),
        user_id=current_user.id
    )

    if data.get('tags'):
        for tag_name in data['tags']:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            task.tags.append(tag)

    db.session.add(task)
    db.session.commit()

    return jsonify(task.to_dict()), 201

@api_bp.route('/tasks/<int:task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    data = request.json

    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.priority = data.get('priority', task.priority)

    if 'due_date' in data:
        task.due_date = datetime.fromisoformat(data['due_date']) if data['due_date'] else None

    if 'status' in data:
        old_status = task.status
        task.status = data['status']
        if old_status != 'completed' and task.status == 'completed':
            task.completed_at = datetime.utcnow()
        elif old_status == 'completed' and task.status != 'completed':
            task.completed_at = None

    if 'tags' in data:
        # Clear existing tags by removing all associations
        for tag in list(task.tags):
            task.tags.remove(tag)
        for tag_name in data['tags']:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
            task.tags.append(tag)

    db.session.commit()
    return jsonify(task.to_dict())

@api_bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    task = Task.query.filter_by(id=task_id, user_id=current_user.id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return '', 204

@api_bp.route('/tasks/stats', methods=['GET'])
@login_required
def get_stats():
    total = Task.query.filter_by(user_id=current_user.id).count()
    completed = Task.query.filter_by(user_id=current_user.id, status='completed').count()
    pending = Task.query.filter_by(user_id=current_user.id, status='pending').count()
    overdue = Task.query.filter(
        Task.user_id == current_user.id,
        Task.due_date < datetime.utcnow(),
        Task.status.in_(['pending', 'in_progress'])
    ).count()

    return jsonify({
        'total': total,
        'completed': completed,
        'pending': pending,
        'overdue': overdue,
        'completion_rate': round((completed / total * 100) if total > 0 else 0, 1)
    })