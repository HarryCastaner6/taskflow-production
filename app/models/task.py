from app import db
from datetime import datetime

task_tags = db.Table('task_tags',
    db.Column('task_id', db.Integer, db.ForeignKey('tasks.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)

class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    priority = db.Column(db.String(20), default='medium')  # low, medium, high, urgent
    status = db.Column(db.String(20), default='pending')  # pending, in_progress, completed, archived
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    board_id = db.Column(db.Integer, db.ForeignKey('boards.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    ai_generated_description = db.Column(db.Boolean, default=False)

    tags = db.relationship('Tag', secondary=task_tags, backref='tasks')

    def is_overdue(self):
        if self.due_date and self.status not in ['completed', 'archived']:
            # Handle both timezone-aware and naive datetimes
            now = datetime.utcnow()
            if self.due_date.tzinfo is not None:
                # If due_date is timezone-aware, convert now to UTC with timezone
                from datetime import timezone
                now = now.replace(tzinfo=timezone.utc)
            return now > self.due_date
        return False

    def mark_complete(self):
        self.status = 'completed'
        self.completed_at = datetime.utcnow()

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'priority': self.priority,
            'status': self.status,
            'is_overdue': self.is_overdue(),
            'board_id': self.board_id,
            'board_name': self.board.name if self.board else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'ai_generated_description': self.ai_generated_description,
            'tags': [tag.name for tag in self.tags]
        }

    def __repr__(self):
        return f'<Task {self.title}>'

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    color = db.Column(db.String(7), default='#6B7280')  # hex color

    def __repr__(self):
        return f'<Tag {self.name}>'