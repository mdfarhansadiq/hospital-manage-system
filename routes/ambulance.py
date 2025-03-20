from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from extensions import db
from models import Ambulance, AmbulanceDispatch, User, Patient
from datetime import datetime

ambulance = Blueprint('ambulance', __name__)

@ambulance.route('/ambulances')
@login_required
def ambulance_list():
    ambulances = Ambulance.query.all()
    return render_template('ambulances.html', ambulances=ambulances)

@ambulance.route('/ambulances/add', methods=['POST'])
@login_required
def add_ambulance():
    try:
        ambulance = Ambulance(
            vehicle_number=request.form['vehicle_number'],
            vehicle_type=request.form['vehicle_type'],
            capacity=request.form['capacity'],
            equipment=request.form['equipment'],
            maintenance_due_date=datetime.strptime(request.form['maintenance_due_date'], '%Y-%m-%d').date()
        )
        db.session.add(ambulance)
        db.session.commit()
        flash('Ambulance added successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding ambulance: {str(e)}')
    return redirect(url_for('ambulance.ambulance_list'))

@ambulance.route('/ambulances/<int:id>/update', methods=['POST'])
@login_required
def update_ambulance(id):
    ambulance = Ambulance.query.get_or_404(id)
    try:
        ambulance.status = request.form['status']
        ambulance.current_location = request.form['current_location']
        ambulance.last_location_update = datetime.utcnow()
        db.session.commit()
        flash('Ambulance status updated successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating ambulance: {str(e)}')
    return redirect(url_for('ambulance.ambulance_list'))

@ambulance.route('/ambulances/dispatch', methods=['POST'])
@login_required
def dispatch_ambulance():
    try:
        ambulance = Ambulance.query.get_or_404(request.form['ambulance_id'])
        if ambulance.status != 'available':
            flash('Selected ambulance is not available')
            return redirect(url_for('ambulance.ambulance_list'))

        dispatch = AmbulanceDispatch(
            ambulance_id=ambulance.id,
            patient_id=request.form.get('patient_id'),
            pickup_location=request.form['pickup_location'],
            destination=request.form['destination'],
            priority_level=request.form['priority_level'],
            notes=request.form.get('notes'),
            dispatched_by_id=current_user.id
        )
        
        ambulance.status = 'busy'
        db.session.add(dispatch)
        db.session.commit()
        flash('Ambulance dispatched successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error dispatching ambulance: {str(e)}')
    return redirect(url_for('ambulance.ambulance_list'))

@ambulance.route('/ambulances/dispatch/<int:id>/complete', methods=['POST'])
@login_required
def complete_dispatch(id):
    dispatch = AmbulanceDispatch.query.get_or_404(id)
    try:
        dispatch.status = 'completed'
        dispatch.completion_time = datetime.utcnow()
        dispatch.ambulance.status = 'available'
        db.session.commit()
        flash('Dispatch marked as completed')
    except Exception as e:
        db.session.rollback()
        flash(f'Error completing dispatch: {str(e)}')
    return redirect(url_for('ambulance.ambulance_list'))