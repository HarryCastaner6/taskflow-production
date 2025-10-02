from app import db
from datetime import datetime

class Board(db.Model):
    __tablename__ = 'boards'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tasks = db.relationship('Task', backref='board', lazy='dynamic', cascade='all, delete-orphan')
    board_access = db.relationship('BoardAccess', backref='board', lazy='dynamic', cascade='all, delete-orphan')

    def has_access(self, user):
        if user.is_admin:
            return True
        if self.owner_id == user.id:
            return True
        return BoardAccess.query.filter_by(
            board_id=self.id,
            user_id=user.id
        ).first() is not None

    def get_users_with_access(self):
        users = []
        for access in self.board_access:
            users.append(access.user)
        if self.owner not in users:
            users.append(self.owner)
        return users

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'owner_id': self.owner_id,
            'owner_username': self.owner.username,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'task_count': self.tasks.count()
        }

    def __repr__(self):
        return f'<Board {self.name}>'


class BoardAccess(db.Model):
    __tablename__ = 'board_access'

    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey('boards.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    can_edit = db.Column(db.Boolean, default=True, nullable=False)
    can_delete = db.Column(db.Boolean, default=False, nullable=False)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    granted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    granted_by = db.relationship('User', foreign_keys=[granted_by_id], backref='granted_accesses')

    __table_args__ = (db.UniqueConstraint('board_id', 'user_id'),)

    def to_dict(self):
        return {
            'id': self.id,
            'board_id': self.board_id,
            'board_name': self.board.name,
            'user_id': self.user_id,
            'username': self.user.username,
            'can_edit': self.can_edit,
            'can_delete': self.can_delete,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None,
            'granted_by': self.granted_by.username if self.granted_by else None
        }

    def __repr__(self):
        return f'<BoardAccess {self.user.username} -> {self.board.name}>'