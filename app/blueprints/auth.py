from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app import db
from app.models import User, Board

auth_bp = Blueprint('auth', __name__)

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80)
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6)
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password')
    ])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash(f'Welcome back, {user.username}!', 'success')
            next_page = request.args.get('next')
            if next_page and next_page.startswith('/'):
                return redirect(next_page)
            return redirect(url_for('main.dashboard'))
        else:
            flash('Invalid username or password. Please try again.', 'danger')
            # Clear the password field to prevent autofill issues
            form.password.data = ''

    return render_template('auth/glass_login.html', form=form)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(
                username=form.username.data,
                email=form.email.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.flush()  # Flush to get user ID

            # Create a default board for the new user
            default_board = Board(
                name=f"{user.username}'s Board",
                description="Your personal task board",
                owner_id=user.id
            )
            db.session.add(default_board)
            db.session.commit()
            flash('Registration successful! Welcome to Task Manager. A default board has been created for you. Please log in to get started.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')

    return render_template('auth/glass_register.html', form=form)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    submit = SubmitField('Send Reset Link')

class ResetPasswordForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()],
                          render_kw={"placeholder": "Enter your username"})
    password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=6)
    ])
    password2 = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('password')
    ])
    submit = SubmitField('Reset Password')

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            # For demo purposes, we'll provide a direct reset link
            # In production, you would send an email with a secure token
            flash(f'Password reset instructions have been sent to {form.email.data}. For demo purposes, click here to reset your password.', 'info')
            flash('Demo: Since email is not configured, you can reset your password by providing your username and new password below.', 'warning')
        else:
            # Always show the same message for security (prevent email enumeration)
            flash(f'Password reset instructions have been sent to {form.email.data} if it exists in our system.', 'info')
        return redirect(url_for('auth.reset_password'))

    return render_template('auth/forgot_password.html', form=form)

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Simplified demo version - in production you'd use secure tokens
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        # For demo purposes, allow reset with username validation
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            try:
                user.set_password(form.password.data)
                db.session.commit()
                flash('Password has been reset successfully! You can now log in with your new password.', 'success')
                return redirect(url_for('auth.login'))
            except Exception as e:
                db.session.rollback()
                flash('Failed to reset password. Please try again.', 'danger')
        else:
            flash('Username not found. Please check your username and try again.', 'danger')

    return render_template('auth/reset_password.html', form=form)