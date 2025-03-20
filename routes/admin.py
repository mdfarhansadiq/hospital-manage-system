from flask import Blueprint, flash, redirect, render_template, request, url_for, jsonify
from flask_login import login_required, current_user
from models import Department, User, db
from functools import wraps

admin = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You need administrative privileges to access this page.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/admin/departments')
@login_required
@admin_required
def departments():
    departments = Department.query.all()
    return render_template('departments.html', departments=departments)

@admin.route('/admin/departments/add', methods=['POST'])
@login_required
@admin_required
def add_department():
    name = request.form.get('name')
    description = request.form.get('description')

    if not name:
        flash('Department name is required.', 'error')
        return redirect(url_for('admin.departments'))

    department = Department(name=name, description=description)
    db.session.add(department)

    try:
        db.session.commit()
        flash('Department added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding department: {str(e)}', 'error')

    return redirect(url_for('admin.departments'))

@admin.route('/admin/departments/<int:id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_department(id):
    department = Department.query.get_or_404(id)

    department.name = request.form.get('name')
    department.description = request.form.get('description')

    try:
        db.session.commit()
        flash('Department updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating department: {str(e)}', 'error')

    return redirect(url_for('admin.departments'))

@admin.route('/api/departments/<int:id>')
@login_required
@admin_required
def get_department(id):
    department = Department.query.get_or_404(id)
    return jsonify({
        'id': department.id,
        'name': department.name,
        'description': department.description
    })

@admin.route('/admin/departments/<int:id>')
@login_required
@admin_required
def view_department(id):
    department = Department.query.get_or_404(id)
    doctors = User.query.filter_by(department_id=id, role='doctor').all()
    return render_template('department_detail.html', department=department, doctors=doctors)