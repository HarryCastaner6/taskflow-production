from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, DateTimeField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length, Optional
from datetime import datetime
from app import db
from app.models import Task, Tag, Board, BoardAccess
from app.utils.audit import log_task_creation, compare_task_changes, log_task_archive, log_task_deletion

tasks_bp = Blueprint('tasks', __name__)

class TaskForm(FlaskForm):
    board_id = SelectField('Board', coerce=int, validators=[DataRequired()])
    title = StringField('Title', validators=[
        DataRequired(),
        Length(max=200)
    ])
    description = TextAreaField('Description', validators=[Optional()])
    due_date = DateTimeField('Due Date', format='%Y-%m-%dT%H:%M', validators=[Optional()])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent')
    ], default='medium')
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('archived', 'Archived')
    ], default='pending')
    tags = StringField('Tags (comma-separated)', validators=[Optional()])
    submit = SubmitField('Save Task')

@tasks_bp.route('/')
@login_required
def list_tasks():
    page = request.args.get('page', 1, type=int)
    per_page = 10
    board_id = request.args.get('board_id', type=int)

    # Get boards accessible to the current user
    if current_user.is_admin:
        accessible_boards = Board.query.filter_by(is_active=True).all()
    else:
        # Get boards owned by user or shared with user
        owned_boards = Board.query.filter_by(owner_id=current_user.id, is_active=True)
        shared_board_ids = db.session.query(BoardAccess.board_id).filter_by(user_id=current_user.id).subquery()
        shared_boards = Board.query.filter(Board.id.in_(shared_board_ids), Board.is_active == True)
        accessible_boards = owned_boards.union(shared_boards).all()

    # Start with base query - tasks in accessible boards
    accessible_board_ids = [board.id for board in accessible_boards]
    if not accessible_board_ids:
        # User has no boards, return empty result
        tasks = Task.query.filter(False).paginate(page=page, per_page=per_page, error_out=False)
        return render_template('tasks/list.html', tasks=tasks, boards=[], selected_board_id=None)

    query = Task.query.filter(Task.board_id.in_(accessible_board_ids))

    # Filter by specific board if requested
    if board_id:
        # Verify user has access to this board
        selected_board = Board.query.get(board_id)
        if selected_board and selected_board.has_access(current_user):
            query = query.filter_by(board_id=board_id)
        else:
            flash('You do not have access to that board.', 'error')
            board_id = None

    # Apply other filters
    status_filter = request.args.get('status')
    if status_filter:
        query = query.filter_by(status=status_filter)

    priority_filter = request.args.get('priority')
    if priority_filter:
        query = query.filter_by(priority=priority_filter)

    search = request.args.get('search')
    if search:
        query = query.filter(
            db.or_(
                Task.title.contains(search),
                Task.description.contains(search)
            )
        )

    sort_by = request.args.get('sort', 'created_at')
    if sort_by == 'due_date':
        query = query.order_by(Task.due_date.asc())
    elif sort_by == 'priority':
        priority_order = db.case(
            {'urgent': 1, 'high': 2, 'medium': 3, 'low': 4},
            value=Task.priority
        )
        query = query.order_by(priority_order)
    else:
        query = query.order_by(Task.created_at.desc())

    tasks = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template('tasks/list.html', tasks=tasks, boards=accessible_boards, selected_board_id=board_id)

@tasks_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = TaskForm()

    # Get boards accessible to the current user for the dropdown
    if current_user.is_admin:
        accessible_boards = Board.query.filter_by(is_active=True).all()
    else:
        # Get boards owned by user or shared with user (with edit permission)
        owned_boards = Board.query.filter_by(owner_id=current_user.id, is_active=True)
        shared_board_ids = db.session.query(BoardAccess.board_id).filter_by(
            user_id=current_user.id, can_edit=True
        ).subquery()
        shared_boards = Board.query.filter(Board.id.in_(shared_board_ids), Board.is_active == True)
        accessible_boards = owned_boards.union(shared_boards).all()

    # Populate board choices - ensure we have boards before proceeding
    if not accessible_boards:
        # Create a default board for the user if they don't have any
        default_board = Board(
            name=f"{current_user.username}'s Board",
            description="Your personal task board",
            owner_id=current_user.id
        )
        db.session.add(default_board)
        db.session.commit()
        accessible_boards = [default_board]
        form.board_id.choices = [(board.id, board.name) for board in accessible_boards]
        flash('A default board has been created for you.', 'info')

    # Update board choices before form validation
    form.board_id.choices = [(board.id, board.name) for board in accessible_boards]

    if form.validate_on_submit():
        # Verify user has access to the selected board
        selected_board = Board.query.get(form.board_id.data)
        if not selected_board or not selected_board.has_access(current_user):
            flash('You do not have access to the selected board.', 'error')
            return render_template('tasks/glass_form.html', form=form, title='Create Task')

        # Verify user has edit permission for this board
        if not current_user.is_admin and selected_board.owner_id != current_user.id:
            board_access = BoardAccess.query.filter_by(
                board_id=selected_board.id, user_id=current_user.id
            ).first()
            if not board_access or not board_access.can_edit:
                flash('You do not have permission to create tasks in this board.', 'error')
                return render_template('tasks/glass_form.html', form=form, title='Create Task')

        task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            priority=form.priority.data,
            status=form.status.data,
            user_id=current_user.id,
            board_id=form.board_id.data
        )

        # Add task to session first
        db.session.add(task)

        if form.tags.data:
            tag_names = [t.strip() for t in form.tags.data.split(',') if t.strip()]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                task.tags.append(tag)
        db.session.flush()  # Flush to get the task ID
        log_task_creation(task)
        db.session.commit()
        flash('Task created successfully!', 'success')
        return redirect(url_for('tasks.list_tasks', board_id=form.board_id.data))

    return render_template('tasks/glass_form.html', form=form, title='Create Task')

@tasks_bp.route('/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(task_id):
    # Get task and verify board access
    task = Task.query.get_or_404(task_id)
    if not task.board.has_access(current_user):
        flash('You do not have access to this task.', 'error')
        return redirect(url_for('tasks.list_tasks'))

    # Check edit permissions
    if not current_user.is_admin and task.board.owner_id != current_user.id:
        board_access = BoardAccess.query.filter_by(
            board_id=task.board_id, user_id=current_user.id
        ).first()
        if not board_access or not board_access.can_edit:
            flash('You do not have permission to edit this task.', 'error')
            return redirect(url_for('tasks.list_tasks'))

    form = TaskForm(obj=task)

    # Get boards accessible to the current user for the dropdown
    if current_user.is_admin:
        accessible_boards = Board.query.filter_by(is_active=True).all()
    else:
        # Get boards owned by user or shared with user (with edit permission)
        owned_boards = Board.query.filter_by(owner_id=current_user.id, is_active=True)
        shared_board_ids = db.session.query(BoardAccess.board_id).filter_by(
            user_id=current_user.id, can_edit=True
        ).subquery()
        shared_boards = Board.query.filter(Board.id.in_(shared_board_ids), Board.is_active == True)
        accessible_boards = owned_boards.union(shared_boards).all()

    # Populate board choices
    form.board_id.choices = [(board.id, board.name) for board in accessible_boards]

    if form.validate_on_submit():
        # Verify user has access to the new board if it's changed
        if form.board_id.data != task.board_id:
            new_board = Board.query.get(form.board_id.data)
            if not new_board or not new_board.has_access(current_user):
                flash('You do not have access to the selected board.', 'error')
                return render_template('tasks/glass_form.html', form=form, title='Edit Task')

            # Verify user has edit permission for the new board
            if not current_user.is_admin and new_board.owner_id != current_user.id:
                board_access = BoardAccess.query.filter_by(
                    board_id=new_board.id, user_id=current_user.id
                ).first()
                if not board_access or not board_access.can_edit:
                    flash('You do not have permission to move tasks to this board.', 'error')
                    return render_template('tasks/glass_form.html', form=form, title='Edit Task')

        # Capture old values for audit
        old_task_data = {
            'title': task.title,
            'description': task.description,
            'due_date': task.due_date,
            'priority': task.priority,
            'status': task.status,
            'board_id': task.board_id
        }

        task.title = form.title.data
        task.description = form.description.data
        task.due_date = form.due_date.data
        task.priority = form.priority.data
        task.board_id = form.board_id.data

        old_status = task.status
        task.status = form.status.data

        if old_status != 'completed' and task.status == 'completed':
            task.completed_at = datetime.utcnow()
        elif old_status == 'completed' and task.status != 'completed':
            task.completed_at = None

        # Capture new values for audit
        new_task_data = {
            'title': task.title,
            'description': task.description,
            'due_date': task.due_date,
            'priority': task.priority,
            'status': task.status,
            'board_id': task.board_id
        }

        # Clear existing tags by removing all associations
        task.tags = []

        if form.tags.data:
            tag_names = [t.strip() for t in form.tags.data.split(',') if t.strip()]
            for tag_name in tag_names:
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                task.tags.append(tag)

        # Log audit trail for changes
        compare_task_changes(old_task_data, new_task_data, task)

        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('tasks.list_tasks', board_id=task.board_id))

    if request.method == 'GET':
        form.tags.data = ', '.join([tag.name for tag in task.tags])

    return render_template('tasks/glass_form.html', form=form, title='Edit Task')

@tasks_bp.route('/<int:task_id>/delete', methods=['POST'])
@login_required
def delete(task_id):
    # Get task and verify board access
    task = Task.query.get_or_404(task_id)
    if not task.board.has_access(current_user):
        flash('You do not have access to this task.', 'error')
        return redirect(url_for('tasks.list_tasks'))

    # Check delete permissions
    if not current_user.is_admin and task.board.owner_id != current_user.id:
        board_access = BoardAccess.query.filter_by(
            board_id=task.board_id, user_id=current_user.id
        ).first()
        if not board_access or not board_access.can_delete:
            flash('You do not have permission to delete this task.', 'error')
            return redirect(url_for('tasks.list_tasks'))

    board_id = task.board_id
    log_task_deletion(task)
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('tasks.list_tasks', board_id=board_id))

@tasks_bp.route('/<int:task_id>/toggle-complete', methods=['POST'])
@login_required
def toggle_complete(task_id):
    # Get task and verify board access
    task = Task.query.get_or_404(task_id)
    if not task.board.has_access(current_user):
        flash('You do not have access to this task.', 'error')
        return redirect(url_for('tasks.list_tasks'))

    # Check edit permissions
    if not current_user.is_admin and task.board.owner_id != current_user.id:
        board_access = BoardAccess.query.filter_by(
            board_id=task.board_id, user_id=current_user.id
        ).first()
        if not board_access or not board_access.can_edit:
            flash('You do not have permission to modify this task.', 'error')
            return redirect(url_for('tasks.list_tasks'))

    if task.status == 'completed':
        task.status = 'pending'
        task.completed_at = None
    else:
        task.mark_complete()

    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'status': task.status})

    flash(f'Task marked as {task.status}!', 'success')
    return redirect(url_for('tasks.list_tasks', board_id=task.board_id))

@tasks_bp.route('/<int:task_id>/archive', methods=['POST'])
@login_required
def archive(task_id):
    # Get task and verify board access
    task = Task.query.get_or_404(task_id)
    if not task.board.has_access(current_user):
        flash('You do not have access to this task.', 'error')
        return redirect(url_for('tasks.list_tasks'))

    # Check edit permissions
    if not current_user.is_admin and task.board.owner_id != current_user.id:
        board_access = BoardAccess.query.filter_by(
            board_id=task.board_id, user_id=current_user.id
        ).first()
        if not board_access or not board_access.can_edit:
            flash('You do not have permission to archive this task.', 'error')
            return redirect(url_for('tasks.list_tasks'))

    task.status = 'archived'
    log_task_archive(task)
    db.session.commit()

    flash('Task archived!', 'success')
    return redirect(url_for('tasks.list_tasks', board_id=task.board_id))