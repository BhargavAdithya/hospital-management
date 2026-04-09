from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from models import User
from forms import LoginForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/')
def role_select():
    return render_template('role_select.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            if user.role == 'receptionist':
                return redirect(url_for('receptionist.dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor.dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.role_select'))