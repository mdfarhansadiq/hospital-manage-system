from datetime import datetime, timedelta
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from app import db
from models import Appointment, User, Patient
from utils.google_calendar import create_calendar_service, get_oauth_flow

appointments = Blueprint('appointments', __name__)

@appointments.route('/appointments')
@login_required
def list_appointments():
    """List all appointments for the logged-in user"""
    if current_user.role == 'doctor':
        appointments = Appointment.query.filter_by(doctor_id=current_user.id).all()
    else:
        appointments = Appointment.query.all()
    return render_template('appointments.html', appointments=appointments)

@appointments.route('/appointments/new', methods=['GET', 'POST'])
@login_required
def new_appointment():
    """Create a new appointment"""
    if request.method == 'POST':
        patient_id = request.form.get('patient_id')
        doctor_id = request.form.get('doctor_id')
        date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        time = datetime.strptime(request.form.get('time'), '%H:%M').time()
        duration = int(request.form.get('duration', 30))
        title = request.form.get('title')
        description = request.form.get('description')

        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            date=date,
            time=time,
            duration=duration,
            title=title,
            description=description
        )

        try:
            # Create the appointment in the database
            db.session.add(appointment)
            db.session.commit()

            # Sync with Google Calendar if credentials are available
            if current_user.google_credentials:
                service = create_calendar_service(current_user.google_credentials)
                appointment.sync_with_calendar(service)
                db.session.commit()

            flash('Appointment created successfully!', 'success')
            return redirect(url_for('appointments.list_appointments'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating appointment: {str(e)}', 'error')

    doctors = User.query.filter_by(role='doctor').all()
    patients = Patient.query.all()
    return render_template('appointments/new.html', doctors=doctors, patients=patients)

@appointments.route('/appointments/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_appointment(id):
    """Edit an existing appointment"""
    appointment = Appointment.query.get_or_404(id)
    
    if request.method == 'POST':
        appointment.date = datetime.strptime(request.form.get('date'), '%Y-%m-%d').date()
        appointment.time = datetime.strptime(request.form.get('time'), '%H:%M').time()
        appointment.duration = int(request.form.get('duration', 30))
        appointment.title = request.form.get('title')
        appointment.description = request.form.get('description')

        try:
            # Update the appointment in Google Calendar if synchronized
            if appointment.calendar_event_id and current_user.google_credentials:
                service = create_calendar_service(current_user.google_credentials)
                appointment.sync_with_calendar(service)

            db.session.commit()
            flash('Appointment updated successfully!', 'success')
            return redirect(url_for('appointments.list_appointments'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating appointment: {str(e)}', 'error')

    doctors = User.query.filter_by(role='doctor').all()
    patients = Patient.query.all()
    return render_template('appointments/edit.html', 
                         appointment=appointment, 
                         doctors=doctors, 
                         patients=patients)

@appointments.route('/appointments/<int:id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(id):
    """Cancel an appointment"""
    appointment = Appointment.query.get_or_404(id)
    appointment.status = 'Cancelled'

    try:
        # Delete the event from Google Calendar if synchronized
        if appointment.calendar_event_id and current_user.google_credentials:
            service = create_calendar_service(current_user.google_credentials)
            service.events().delete(calendarId='primary', 
                                 eventId=appointment.calendar_event_id).execute()
            appointment.calendar_event_id = None

        db.session.commit()
        flash('Appointment cancelled successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error cancelling appointment: {str(e)}', 'error')

    return redirect(url_for('appointments.list_appointments'))
