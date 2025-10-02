from app import db
from datetime import datetime

class TaskAudit(db.Model):
    __tablename__ = 'task_audits'

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # created, updated, completed, archived, deleted
    field_name = db.Column(db.String(50))  # field that was changed (for updates)
    old_value = db.Column(db.Text)  # old value
    new_value = db.Column(db.Text)  # new value
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))  # support IPv6
    user_agent = db.Column(db.Text)

    # Relationships
    task = db.relationship('Task', backref='audit_logs')
    user = db.relationship('User', backref='audit_actions')

    def to_dict(self):
        return {
            'id': self.id,
            'task_id': self.task_id,
            'user_id': self.user_id,
            'action': self.action,
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'timestamp': self.timestamp.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }

    def get_description(self):
        """Get a human-readable description of the audit entry"""
        if self.action == 'created':
            return f"Task created"
        elif self.action == 'updated' and self.field_name:
            return f"Changed {self.field_name.replace('_', ' ')} from '{self.old_value}' to '{self.new_value}'"
        elif self.action == 'completed':
            return "Task marked as completed"
        elif self.action == 'archived':
            return "Task archived"
        elif self.action == 'deleted':
            return "Task deleted"
        else:
            return f"Action: {self.action}"

    def __repr__(self):
        return f'<TaskAudit {self.action} on Task {self.task_id}>'