from flask import request
from flask_login import current_user
from app import db
from app.models.audit import TaskAudit

def log_task_action(task, action, field_name=None, old_value=None, new_value=None):
    """
    Log a task action to the audit trail

    Args:
        task: Task instance
        action: string describing the action (created, updated, completed, archived, deleted)
        field_name: name of the field that was changed (for updates)
        old_value: previous value (for updates)
        new_value: new value (for updates)
    """
    audit_entry = TaskAudit(
        task_id=task.id,
        user_id=current_user.id,
        action=action,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.environ.get('HTTP_USER_AGENT')
    )

    db.session.add(audit_entry)
    # Note: Don't commit here, let the calling function handle the transaction

def log_task_creation(task):
    """Log task creation"""
    log_task_action(task, 'created')

def log_task_update(task, field_name, old_value, new_value):
    """Log task field update"""
    if old_value != new_value:
        log_task_action(task, 'updated', field_name, old_value, new_value)

def log_task_completion(task):
    """Log task completion"""
    log_task_action(task, 'completed')

def log_task_archive(task):
    """Log task archival"""
    log_task_action(task, 'archived')

def log_task_deletion(task):
    """Log task deletion"""
    log_task_action(task, 'deleted')

def compare_task_changes(old_task_data, new_task_data, task):
    """
    Compare old and new task data and log all changes

    Args:
        old_task_data: dict with old values
        new_task_data: dict with new values
        task: Task instance
    """
    fields_to_track = ['title', 'description', 'due_date', 'priority', 'status']

    for field in fields_to_track:
        old_value = old_task_data.get(field)
        new_value = new_task_data.get(field)

        # Special handling for due_date
        if field == 'due_date':
            old_value = old_value.isoformat() if old_value else None
            new_value = new_value.isoformat() if new_value else None

        if old_value != new_value:
            log_task_update(task, field, old_value, new_value)