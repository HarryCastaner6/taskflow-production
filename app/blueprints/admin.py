from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import User, Board, BoardAccess, Task
from werkzeug.security import generate_password_hash

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin')

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You must be an admin to access this page.', 'danger')
            return redirect(url_for('main.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Get comprehensive stats
    stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_admin=False).count(),
        'total_boards': Board.query.filter_by(is_active=True).count(),
        'total_tasks': Task.query.count()
    }

    recent_users = User.query.order_by(User.created_at.desc()).limit(6).all()
    recent_boards = Board.query.order_by(Board.created_at.desc()).limit(6).all()

    # Mock recent activities for demonstration
    recent_activities = [
        {
            'type': 'user_created',
            'description': f'New user {recent_users[0].username} joined' if recent_users else 'User activity',
            'timestamp': recent_users[0].created_at if recent_users else None
        },
        {
            'type': 'board_created',
            'description': f'Board "{recent_boards[0].name}" created' if recent_boards else 'Board activity',
            'timestamp': recent_boards[0].created_at if recent_boards else None
        }
    ] if recent_users and recent_boards else []

    return render_template('glass_admin_dashboard.html',
                         stats=stats,
                         recent_users=recent_users,
                         recent_boards=recent_boards,
                         recent_activities=recent_activities)

# User Management Routes
@admin_bp.route('/admin/users')
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('manage_users.html', users=users)

@admin_bp.route('/admin/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        is_admin = request.form.get('is_admin') == 'on'

        # Check if user exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            flash('A user with this username or email already exists.', 'danger')
            return redirect(url_for('admin.create_user'))

        # Create new user
        user = User(username=username, email=email, is_admin=is_admin)
        user.set_password(password)

        # Create a default personal board for the user
        personal_board = Board(
            name=f"{username}'s Personal Board",
            description="Personal task board",
            owner=user
        )

        db.session.add(user)
        db.session.add(personal_board)
        db.session.commit()

        flash(f'User {username} created successfully!', 'success')
        return redirect(url_for('admin.manage_users'))

    return render_template('create_user.html')

@admin_bp.route('/admin/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.is_admin = request.form.get('is_admin') == 'on'

        if request.form.get('password'):
            user.set_password(request.form.get('password'))

        db.session.commit()
        flash(f'User {user.username} updated successfully!', 'success')
        return redirect(url_for('admin.manage_users'))

    return render_template('edit_user.html', user=user)

@admin_bp.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('You cannot delete your own account.', 'danger')
        return redirect(url_for('admin.manage_users'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(f'User {username} deleted successfully!', 'success')
    return redirect(url_for('admin.manage_users'))

# Board Management Routes
@admin_bp.route('/admin/boards')
@admin_required
def manage_boards():
    boards = Board.query.order_by(Board.created_at.desc()).all()
    return render_template('manage_boards.html', boards=boards)

@admin_bp.route('/admin/boards/create', methods=['GET', 'POST'])
@admin_required
def create_board():
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        owner_id = request.form.get('owner_id')

        board = Board(
            name=name,
            description=description,
            owner_id=owner_id
        )

        db.session.add(board)
        db.session.commit()

        # Add selected users to board access
        user_ids = request.form.getlist('user_ids')
        for user_id in user_ids:
            if int(user_id) != int(owner_id):  # Don't add owner as they already have access
                access = BoardAccess(
                    board_id=board.id,
                    user_id=user_id,
                    can_edit=True,
                    can_delete=False,
                    granted_by_id=current_user.id
                )
                db.session.add(access)

        db.session.commit()
        flash(f'Board "{name}" created successfully!', 'success')
        return redirect(url_for('admin.manage_boards'))

    users = User.query.order_by(User.username).all()
    return render_template('create_board.html', users=users)

@admin_bp.route('/admin/boards/<int:board_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_board(board_id):
    board = Board.query.get_or_404(board_id)

    if request.method == 'POST':
        board.name = request.form.get('name')
        board.description = request.form.get('description')
        board.owner_id = request.form.get('owner_id')

        # Update board access
        BoardAccess.query.filter_by(board_id=board.id).delete()

        user_ids = request.form.getlist('user_ids')
        for user_id in user_ids:
            if int(user_id) != board.owner_id:
                access = BoardAccess(
                    board_id=board.id,
                    user_id=user_id,
                    can_edit=True,
                    can_delete=False,
                    granted_by_id=current_user.id
                )
                db.session.add(access)

        db.session.commit()
        flash(f'Board "{board.name}" updated successfully!', 'success')
        return redirect(url_for('admin.manage_boards'))

    users = User.query.order_by(User.username).all()
    current_access = BoardAccess.query.filter_by(board_id=board.id).all()
    user_ids_with_access = [access.user_id for access in current_access]

    return render_template('edit_board.html',
                         board=board,
                         users=users,
                         user_ids_with_access=user_ids_with_access)

@admin_bp.route('/admin/boards/<int:board_id>/delete', methods=['POST'])
@admin_required
def delete_board(board_id):
    board = Board.query.get_or_404(board_id)
    board_name = board.name

    db.session.delete(board)
    db.session.commit()

    flash(f'Board "{board_name}" deleted successfully!', 'success')
    return redirect(url_for('admin.manage_boards'))

@admin_bp.route('/admin/boards/<int:board_id>/access')
@admin_required
def manage_board_access(board_id):
    board = Board.query.get_or_404(board_id)
    access_list = BoardAccess.query.filter_by(board_id=board_id).all()
    available_users = User.query.filter(
        ~User.id.in_([access.user_id for access in access_list] + [board.owner_id])
    ).all()

    return render_template('manage_board_access.html',
                         board=board,
                         access_list=access_list,
                         available_users=available_users)

@admin_bp.route('/admin/boards/<int:board_id>/access/add', methods=['POST'])
@admin_required
def add_board_access(board_id):
    board = Board.query.get_or_404(board_id)
    user_id = request.form.get('user_id')
    can_edit = request.form.get('can_edit') == 'on'
    can_delete = request.form.get('can_delete') == 'on'

    # Check if access already exists
    existing = BoardAccess.query.filter_by(
        board_id=board_id,
        user_id=user_id
    ).first()

    if existing:
        flash('User already has access to this board.', 'warning')
    else:
        access = BoardAccess(
            board_id=board_id,
            user_id=user_id,
            can_edit=can_edit,
            can_delete=can_delete,
            granted_by_id=current_user.id
        )
        db.session.add(access)
        db.session.commit()
        flash('Access granted successfully!', 'success')

    return redirect(url_for('admin.manage_board_access', board_id=board_id))

@admin_bp.route('/admin/boards/access/<int:access_id>/remove', methods=['POST'])
@admin_required
def remove_board_access(access_id):
    access = BoardAccess.query.get_or_404(access_id)
    board_id = access.board_id

    db.session.delete(access)
    db.session.commit()
    flash('Access removed successfully!', 'success')

    return redirect(url_for('admin.manage_board_access', board_id=board_id))