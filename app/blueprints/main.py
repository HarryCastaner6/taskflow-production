from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, and_, or_
from app.models import Task, Board, BoardAccess, User
from app import db
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    # Get accessible boards for the user
    user_boards = Board.query.filter(
        or_(
            Board.owner_id == current_user.id,
            Board.id.in_(
                db.session.query(BoardAccess.board_id)
                .filter_by(user_id=current_user.id)
            )
        )
    ).filter_by(is_active=True).all()

    # Get tasks from all accessible boards
    board_ids = [board.id for board in user_boards]
    user_tasks = Task.query.filter(
        or_(
            Task.user_id == current_user.id,
            Task.board_id.in_(board_ids)
        )
    )

    tasks_by_status = {
        'pending': user_tasks.filter_by(status='pending').all(),
        'in_progress': user_tasks.filter_by(status='in_progress').all(),
        'completed': user_tasks.filter_by(status='completed').limit(10).all()
    }

    # Calculate date ranges
    today = datetime.utcnow().date()
    week_from_now = today + timedelta(days=7)

    overdue_tasks = user_tasks.filter(
        Task.due_date < datetime.utcnow(),
        Task.status.in_(['pending', 'in_progress'])
    ).all()

    # Upcoming tasks (due within next 7 days)
    upcoming_tasks = user_tasks.filter(
        and_(
            Task.due_date >= datetime.combine(today, datetime.min.time()),
            Task.due_date <= datetime.combine(week_from_now, datetime.max.time()),
            Task.status.in_(['pending', 'in_progress'])
        )
    ).order_by(Task.due_date.asc()).limit(5).all()

    stats = {
        'total': user_tasks.count(),
        'completed': user_tasks.filter_by(status='completed').count(),
        'pending': user_tasks.filter_by(status='pending').count(),
        'overdue': len(overdue_tasks),
        'boards': len(user_boards)
    }

    # Calculate completion rate
    if stats['total'] > 0:
        stats['completion_rate'] = round((stats['completed'] / stats['total']) * 100, 1)
    else:
        stats['completion_rate'] = 0

    # Priority counts for charts
    priority_counts = {
        'low': user_tasks.filter_by(priority='low').count(),
        'medium': user_tasks.filter_by(priority='medium').count(),
        'high': user_tasks.filter_by(priority='high').count(),
        'urgent': user_tasks.filter_by(priority='urgent').count()
    }

    recent_tasks = user_tasks.order_by(Task.created_at.desc()).limit(8).all()

    # Get team members from all accessible boards
    team_members = set()
    for board in user_boards:
        team_members.update(board.get_users_with_access())

    # Remove current user from team members
    team_members.discard(current_user)
    team_members = list(team_members)[:8]  # Limit to 8 members

    # Get recent activity (tasks created/updated in last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_activity = user_tasks.filter(
        or_(
            Task.created_at >= week_ago,
            Task.updated_at >= week_ago
        )
    ).order_by(Task.updated_at.desc()).limit(10).all()

    return render_template('glass_dashboard.html',
        tasks_by_status=tasks_by_status,
        overdue_tasks=overdue_tasks,
        upcoming_tasks=upcoming_tasks,
        stats=stats,
        priority_counts=priority_counts,
        recent_tasks=recent_tasks,
        user_boards=user_boards,
        team_members=team_members,
        recent_activity=recent_activity
    )

@main_bp.route('/boards')
@login_required
def boards():
    """Boards management page with filtering"""
    filter_type = request.args.get('filter', 'all')
    search = request.args.get('search', '')

    # Base query for boards accessible to user
    query = Board.query.filter(
        or_(
            Board.owner_id == current_user.id,
            Board.id.in_(
                db.session.query(BoardAccess.board_id)
                .filter_by(user_id=current_user.id)
            )
        )
    )

    # Apply filters
    if filter_type == 'owned':
        query = query.filter_by(owner_id=current_user.id)
    elif filter_type == 'shared':
        query = query.filter(
            Board.owner_id != current_user.id,
            Board.id.in_(
                db.session.query(BoardAccess.board_id)
                .filter_by(user_id=current_user.id)
            )
        )
    elif filter_type == 'active':
        query = query.filter_by(is_active=True)

    if search:
        query = query.filter(
            or_(
                Board.name.ilike(f'%{search}%'),
                Board.description.ilike(f'%{search}%')
            )
        )

    boards = query.order_by(Board.updated_at.desc()).all()

    # Get board statistics
    board_stats = {}
    for board in boards:
        task_count = board.tasks.count()
        completed_count = board.tasks.filter_by(status='completed').count()
        board_stats[board.id] = {
            'total_tasks': task_count,
            'completed_tasks': completed_count,
            'completion_rate': round((completed_count / task_count * 100) if task_count > 0 else 0, 1),
            'member_count': len(board.get_users_with_access())
        }

    return render_template('boards/list.html',
        boards=boards,
        board_stats=board_stats,
        filter_type=filter_type,
        search=search
    )

# Add helpful redirect routes
@main_bp.route('/app')
@main_bp.route('/home')
def app_redirect():
    """Redirect common URLs to appropriate pages"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.index'))

# Placeholder routes for Settings, Reports, and Teams pages
@main_bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('settings.html')

@main_bp.route('/reports')
@login_required
def reports():
    """Reports and analytics page"""
    # Get basic stats for reports
    user_boards = Board.query.filter(
        or_(
            Board.owner_id == current_user.id,
            Board.id.in_(
                db.session.query(BoardAccess.board_id)
                .filter_by(user_id=current_user.id)
            )
        )
    ).filter_by(is_active=True).all()

    board_ids = [board.id for board in user_boards]
    user_tasks = Task.query.filter(
        or_(
            Task.user_id == current_user.id,
            Task.board_id.in_(board_ids)
        )
    )

    stats = {
        'total_tasks': user_tasks.count(),
        'completed_tasks': user_tasks.filter_by(status='completed').count(),
        'pending_tasks': user_tasks.filter_by(status='pending').count(),
        'in_progress_tasks': user_tasks.filter_by(status='in_progress').count(),
        'total_boards': len(user_boards)
    }

    return render_template('reports.html', stats=stats, user_boards=user_boards)

@main_bp.route('/teams')
@login_required
def teams():
    """Teams and collaboration page"""
    # Get teams (boards where user has access)
    user_boards = Board.query.filter(
        or_(
            Board.owner_id == current_user.id,
            Board.id.in_(
                db.session.query(BoardAccess.board_id)
                .filter_by(user_id=current_user.id)
            )
        )
    ).filter_by(is_active=True).all()

    # Get team members from all accessible boards
    team_members = set()
    for board in user_boards:
        team_members.update(board.get_users_with_access())

    # Remove current user from team members
    team_members.discard(current_user)
    team_members = list(team_members)

    return render_template('teams.html', user_boards=user_boards, team_members=team_members)