import os
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
import logging
from werkzeug.utils import secure_filename
from functools import wraps
import csv
from io import StringIO
from sqlalchemy import func, Time

from extensions import db

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# create the app
app = Flask(__name__)
# setup a secret key, required by sessions
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
# configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital_tracker.db'  # For SQLite
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension
db.init_app(app)
migrate = Migrate(app, db)

# Initialize login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

with app.app_context():
    # Import models after db initialization
    from models import User, Patient, Appointment, Bed, Ward, InventoryItem, InventoryBatch, InventoryTransaction, Supplier, AutomatedOrder, AdmissionQueue, Admission, Prescription, PrescriptionMedication, LabTest, LabTestCategory, MedicalHistory, PatientAllergy, PatientDocument
    # Import and register blueprints
    from routes.admin import admin
    from routes.ambulance import ambulance
    app.register_blueprint(admin)
    app.register_blueprint(ambulance)

    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'total_patients': Patient.query.count(),
        'total_appointments': Appointment.query.count(),
        'available_beds': Bed.query.filter_by(occupied=False).count(),
        'total_staff': User.query.count()
    }
    return render_template('dashboard.html', stats=stats)

@app.route('/patients')
@login_required
def patient_list():
    return render_template('patients.html', patients=Patient.query.all())

@app.route('/appointments')
@login_required
def appointment_list():
    from datetime import date
    appointments = Appointment.query.all()
    doctors = User.query.filter_by(role='doctor').all()
    patients = Patient.query.all()
    return render_template('appointments.html',
                         appointments=appointments,
                         doctors=doctors,
                         patients=patients,
                         today=date.today())

@app.route('/staff')
@login_required
def staff_list():
    return render_template('staff.html', staff=User.query.all())

@app.route('/wards')
@login_required
def ward_list():
    return render_template('wards.html', wards=Ward.query.all(), beds=Bed.query.all())

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/prescriptions')
@login_required
def prescription_list():
    from models import Prescription, Patient
    prescriptions = Prescription.query.all()
    patients = Patient.query.all()
    return render_template('prescriptions.html', 
                         prescriptions=prescriptions,
                         patients=patients,
                         today=date.today())

@app.route('/prescriptions/add', methods=['POST'])
@login_required
def add_prescription():
    from models import Prescription, PrescriptionMedication
    if request.method == 'POST':
        try:
            prescription = Prescription(
                patient_id=request.form['patient_id'],
                doctor_id=current_user.id,
                date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
                diagnosis=request.form['diagnosis'],
                notes=request.form.get('notes', '')
            )
            db.session.add(prescription)
            db.session.flush()  # Get the prescription ID

            # Handle medications
            medications = request.form.getlist('medications[]')
            dosages = request.form.getlist('dosages[]')
            frequencies = request.form.getlist('frequencies[]')
            durations = request.form.getlist('durations[]')
            instructions = request.form.getlist('instructions[]')

            for i in range(len(medications)):
                medication = PrescriptionMedication(
                    prescription_id=prescription.id,
                    medication_name=medications[i],
                    dosage=dosages[i],
                    frequency=frequencies[i],
                    duration=durations[i],
                    instructions=instructions[i] if i < len(instructions) else None
                )
                db.session.add(medication)

            db.session.commit()
            flash('Prescription added successfully')
            return redirect(url_for('prescription_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding prescription: {str(e)}')
            return redirect(url_for('prescription_list'))

@app.route('/prescriptions/<int:id>')
@login_required
def view_prescription(id):
    from models import Prescription
    prescription = Prescription.query.get_or_404(id)
    return jsonify({
        'id': prescription.id,
        'patient': prescription.patient.name,
        'doctor': prescription.doctor.name,
        'date': prescription.date.strftime('%Y-%m-%d'),
        'diagnosis': prescription.diagnosis,
        'medications': [{
            'name': med.medication_name,
            'dosage': med.dosage,
            'frequency': med.frequency,
            'duration': med.duration,
            'instructions': med.instructions
        } for med in prescription.medications],
        'notes': prescription.notes,
        'status': prescription.status
    })

@app.route('/laboratory')
@login_required
def laboratory_list():
    from models import LabTest, Patient, LabTestCategory
    lab_tests = LabTest.query.all()
    patients = Patient.query.all()
    categories = LabTestCategory.query.all()
    return render_template('laboratory.html', 
                         lab_tests=lab_tests,
                         patients=patients,
                         categories=categories)

@app.route('/laboratory/add', methods=['POST'])
@login_required
def add_lab_test():
    from models import LabTest
    if request.method == 'POST':
        try:
            lab_test = LabTest(
                patient_id=request.form['patient_id'],
                doctor_id=current_user.id,
                category_id=request.form['category_id'],
                test_date=datetime.strptime(request.form['test_date'], '%Y-%m-%dT%H:%M'),
                priority=request.form['priority'],
                notes=request.form.get('notes', '')
            )
            db.session.add(lab_test)
            db.session.commit()
            flash('Laboratory test added successfully')
            return redirect(url_for('laboratory_list'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding laboratory test: {str(e)}')
            return redirect(url_for('laboratory_list'))

@app.route('/laboratory/<int:id>')
@login_required
def view_lab_test(id):
    from models import LabTest
    lab_test = LabTest.query.get_or_404(id)
    return jsonify({
        'id': lab_test.id,
        'patient': lab_test.patient.name,
        'doctor': lab_test.doctor.name,
        'category': lab_test.category.name,
        'test_date': lab_test.test_date.strftime('%Y-%m-%d %H:%M'),
        'priority': lab_test.priority,
        'status': lab_test.status,
        'notes': lab_test.notes,
        'results': [{
            'parameter': result.parameter_name,
            'value': result.value,
            'unit': result.unit,
            'reference_range': result.reference_range,
            'is_abnormal': result.is_abnormal,
            'notes': result.notes
        } for result in lab_test.results]
    })

@app.route('/patients/<int:id>')
@login_required
def patient_detail(id):
    from models import Patient, Ward
    from utils.wellness import generate_wellness_tip

    patient = Patient.query.get_or_404(id)
    wards = Ward.query.all()  # Get all wards for admission modal

    # Initialize tip_data with a default state
    tip_data = {
        'success': False,
        'tip': 'Click the "Get Wellness Tip" button to generate a personalized tip.',
        'generated_at': datetime.utcnow()
    }

    return render_template('patient_detail.html', 
                         patient=patient, 
                         wards=wards,
                         tip_data=tip_data)

@app.route('/patients/<int:id>/update', methods=['POST'])
@login_required
def update_patient(id):
    from models import Patient
    patient = Patient.query.get_or_404(id)
    try:
        patient.name = request.form['name']
        patient.age = request.form['age']
        patient.gender = request.form['gender']
        patient.contact = request.form['contact']
        patient.email = request.form.get('email')
        patient.address = request.form.get('address')
        patient.blood_type = request.form.get('blood_type')
        patient.date_of_birth = datetime.strptime(request.form['date_of_birth'], '%Y-%m-%d').date() if request.form.get('date_of_birth') else None
        patient.emergency_contact_name = request.form.get('emergency_contact_name')
        patient.emergency_contact_number = request.form.get('emergency_contact_number')
        patient.insurance_provider = request.form.get('insurance_provider')
        patient.insurance_number = request.form.get('insurance_number')

        db.session.commit()
        flash('Patient information updated successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating patient information: {str(e)}')
    return redirect(url_for('patient_detail', id=id))

@app.route('/patients/<int:id>/vitals/add', methods=['POST'])
@login_required
def add_vitals(id):
    from models import VitalSign
    try:
        vital_sign = VitalSign(
            patient_id=id,
            temperature=request.form.get('temperature'),
            blood_pressure_systolic=request.form.get('blood_pressure_systolic'),
            blood_pressure_diastolic=request.form.get('blood_pressure_diastolic'),
            heart_rate=request.form.get('heart_rate'),
            respiratory_rate=request.form.get('respiratory_rate'),
            oxygen_saturation=request.form.get('oxygen_saturation'),
            notes=request.form.get('notes'),
            recorded_by_id=current_user.id
        )
        db.session.add(vital_sign)
        db.session.commit()
        flash('Vital signs recorded successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error recording vital signs: {str(e)}')
    return redirect(url_for('patient_detail', id=id))

@app.route('/patients/<int:id>/allergies/add', methods=['POST'])
@login_required
def add_allergy(id):
    from models import PatientAllergy
    try:
        allergy = PatientAllergy(
            patient_id=id,
            allergen=request.form['allergen'],
            severity=request.form['severity'],
            reaction=request.form['reaction'],
            diagnosis_date=datetime.strptime(request.form['diagnosis_date'], '%Y-%m-%d').date() if request.form.get('diagnosis_date') else None,
            notes=request.form.get('notes')
        )
        db.session.add(allergy)
        db.session.commit()
        flash('Allergy information added successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding allergy information: {str(e)}')
    return redirect(url_for('patient_detail', id=id))

@app.route('/patients/<int:id>/medical-history/add', methods=['POST'])
@login_required
def add_medical_history(id):
    from models import MedicalHistory
    try:
        history = MedicalHistory(
            patient_id=id,
            condition=request.form['condition'],
            diagnosis_date=datetime.strptime(request.form['diagnosis_date'], '%Y-%m-%d').date() if request.form.get('diagnosis_date') else None,
            treatment=request.form['treatment'],
            status=request.form['status'],
            notes=request.form.get('notes')
        )
        db.session.add(history)
        db.session.commit()
        flash('Medical history entry added successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding medical history: {str(e)}')
    return redirect(url_for('patient_detail', id=id))

@app.route('/patients/<int:id>/documents/upload', methods=['POST'])
@login_required
def upload_document(id):
    if 'document' not in request.files:
        flash('No file selected')
        return redirect(url_for('patient_detail', id=id))

    file = request.files['document']
    if file.filename == '':
        flash('No file selected')
        return redirect(url_for('patient_detail', id=id))

    try:
        from models import PatientDocument
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', 'patient_documents', filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        file.save(file_path)

        document = PatientDocument(
            patient_id=id,
            document_type=request.form['document_type'],
            title=request.form['title'],
            file_path=file_path,
            notes=request.form.get('notes'),
            uploaded_by_id=current_user.id
        )
        db.session.add(document)
        db.session.commit()
        flash('Document uploaded successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error uploading document: {str(e)}')
    return redirect(url_for('patient_detail', id=id))


@app.route('/patients/<int:id>/admit', methods=['POST'])
@login_required
def admit_patient(id):
    from models import Patient, Admission, Bed, AdmissionQueue, PRIORITY_LEVELS
    try:
        patient = Patient.query.get_or_404(id)

        # Check if patient is already admitted or in queue
        if patient.current_admission:
            flash('Patient is already admitted or in queue')
            return redirect(url_for('patient_detail', id=id))

        priority_level = request.form.get('priority_level', 'routine')
        if priority_level not in PRIORITY_LEVELS:
            priority_level = 'routine'

        # Create admission record with priority
        admission = Admission(
            patient_id=id,
            admission_reason=request.form['admission_reason'],
            admission_notes=request.form.get('admission_notes'),
            attending_doctor_id=current_user.id,
            priority_level=priority_level,
            priority_score=PRIORITY_LEVELS[priority_level],
            expected_duration=request.form.get('expected_duration', 1)
        )

        # If a bed is specified and available, assign it
        bed_id = request.form.get('bed_id')
        if bed_id:
            bed = Bed.query.get_or_404(bed_id)
            if not bed.occupied:
                admission.bed_id = bed_id
                admission.status = 'active'
                bed.occupied = True
                bed.patient_id = id
            else:
                # If bed is occupied, add to queue
                admission.status = 'waiting'
                queue_entry = AdmissionQueue(
                    admission=admission,
                    ward_type_needed=request.form['ward_type'],
                    special_requirements=request.form.get('special_requirements')
                )
                db.session.add(queue_entry)
        else:
            # No bed specified, add to queue
            admission.status = 'waiting'
            queue_entry = AdmissionQueue(
                admission=admission,
                ward_type_needed=request.form['ward_type'],
                special_requirements=request.form.get('special_requirements')
            )
            db.session.add(queue_entry)

        db.session.add(admission)
        db.session.commit()

        if admission.status == 'active':
            flash('Patient admitted successfully')
        else:
            flash('Patient added to admission queue')

    except Exception as e:
        db.session.rollback()
        flash(f'Error processing admission: {str(e)}')
    return redirect(url_for('patient_detail', id=id))

@app.route('/patients/<int:id>/discharge', methods=['POST'])
@login_required
def discharge_patient(id):
    from models import Patient, Admission
    try:
        patient = Patient.query.get_or_404(id)
        admission = patient.current_admission

        if not admission:
            flash('Patient is not currently admitted')
            return redirect(url_for('patient_detail', id=id))

        # Update admission record
        admission.discharge_date = datetime.utcnow()
        admission.status = 'discharged'

        # Free up the bed
        bed = admission.bed
        bed.occupied = False
        bed.patient_id = None

        db.session.commit()
        flash('Patient discharged successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error discharging patient: {str(e)}')
    return redirect(url_for('patient_detail', id=id))

@app.route('/admissions')
@login_required
def admission_list():
    from models import Admission
    # Get both active and waiting admissions, ordered by priority score for waiting ones
    admissions = Admission.query.filter(
        Admission.status.in_(['active', 'waiting'])
    ).order_by(
        # Put active admissions first, then order waiting ones by priority score
        Admission.status.desc(),
        Admission.priority_score.asc(),
        Admission.admission_date.asc()
    ).all()
    return render_template('admissions.html', admissions=admissions)

@app.route('/admissions/analytics')
@login_required
def admission_analytics():
    from models import Admission, Ward, AdmissionQueue, Bed
    # Calculate average length of stay for completed admissions
    avg_stay = db.session.query(
        func.avg(
            func.extract('epoch', Admission.discharge_date - Admission.admission_date) / 86400
        )
    ).filter(
        Admission.status == 'discharged'
    ).scalar() or 0

    # Get admission counts by priority level
    priority_distribution = db.session.query(
        Admission.priority_level,
        func.count(Admission.id)
    ).group_by(
        Admission.priority_level
    ).all()

    # Get admission counts by month for the last 12 months
    monthly_trends = db.session.query(
        func.date_trunc('month', Admission.admission_date),
        func.count(Admission.id)
    ).group_by(
        func.date_trunc('month', Admission.admission_date)
    ).order_by(
        func.date_trunc('month', Admission.admission_date).desc()
    ).limit(12).all()

    # Calculate current ward occupancy rates - Fixed query
    ward_occupancy = db.session.query(
        Ward.name,
        func.count(Admission.id).filter(Admission.status == 'active').label('occupied'),
        func.count(Bed.id).label('total')
    ).join(
        Bed, Ward.id == Bed.ward_id
    ).outerjoin(
        Admission, Admission.bed_id == Bed.id
    ).group_by(
        Ward.id, Ward.name
    ).all()

    # Get common admission reasons
    common_reasons = db.session.query(
        Admission.admission_reason,
        func.count(Admission.id).label('count')
    ).group_by(
        Admission.admission_reason
    ).order_by(
        func.count(Admission.id).desc()
    ).limit(10).all()

    # Get current queue statistics
    queue_stats = {
        'total_waiting': AdmissionQueue.query.count(),
        'high_priority': AdmissionQueue.query.join(Admission).filter(
            Admission.priority_level == 'high'
        ).count(),
        'avg_wait_time': db.session.query(
            func.avg(
                func.extract('epoch', func.now() - Admission.admission_date) / 3600
            )
        ).join(
            AdmissionQueue
        ).filter(
            Admission.status == 'waiting'
        ).scalar() or 0
    }

    return render_template(
        'admission_analytics.html',
        avg_stay=round(avg_stay, 1),
        priority_distribution=priority_distribution,
        monthly_trends=monthly_trends,
        ward_occupancy=ward_occupancy,
        common_reasons=common_reasons,
        queue_stats=queue_stats
    )

@app.route('/admissions/report/generate')
@login_required
def generate_admission_report():
    from models import Admission, Ward
    from datetime import datetime, timedelta

    # Get date range from query parameters or default to last 30 days
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    # Query admissions within the date range
    admissions = Admission.query.filter(
        Admission.admission_date.between(start_date, end_date)
    ).order_by(
        Admission.admission_date.desc()
    ).all()

    # Create CSV data
    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow([
        'Admission ID', 'Patient Name', 'Admission Date', 'Discharge Date',
        'Length of Stay (days)', 'Priority Level', 'Ward', 'Bed Number',
        'Admission Reason', 'Status'
    ])

    # Write admission data
    for admission in admissions:
        length_of_stay = None
        if admission.discharge_date:
            length_of_stay = (admission.discharge_date - admission.admission_date).days

        writer.writerow([
            admission.id,
            admission.patient.name,
            admission.admission_date.strftime('%Y-%m-%d %H:%M'),
            admission.discharge_date.strftime('%Y-%m-%d %H:%M') if admission.discharge_date else 'N/A',
            length_of_stay if length_of_stay is not None else 'N/A',
            admission.priority_level,
            admission.bed.ward.name if admission.bed else 'N/A',
            admission.bed.number if admission.bed else 'N/A',
            admission.admission_reason,
            admission.status
        ])

    # Create response
    output = si.getvalue()
    si.close()

    response = app.make_response(output)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=admission_report_{datetime.now().strftime("%Y%m%d")}.csv'

    return response

@app.route('/patients/<int:id>/export', methods=['GET'])
@login_required
def export_patient_data(id):
    from models import Patient
    patient = Patient.query.get_or_404(id)

    # Create a string buffer to write CSV data
    si = StringIO()
    writer = csv.writer(si)

    # Write patient basic information
    writer.writerow(['Patient Information'])
    writer.writerow(['ID', 'Name', 'Age', 'Gender', 'Contact', 'Email', 'Blood Type'])
    writer.writerow([
        patient.id, patient.name, patient.age, patient.gender,
        patient.contact, patient.email or '', patient.blood_type or ''
    ])

    # Write vital signs
    writer.writerow([])  # Empty row for spacing
    writer.writerow(['Vital Signs'])
    writer.writerow(['Date', 'Temperature', 'Blood Pressure', 'Heart Rate', 'Respiratory Rate', 'Oxygen Saturation'])
    for vital in patient.vital_signs:
        writer.writerow([
            vital.measured_at.strftime('%Y-%m-%d %H:%M'),
            vital.temperature or '',
            f"{vital.blood_pressure_systolic}/{vital.blood_pressure_diastolic}" if vital.blood_pressure_systolic else '',
            vital.heart_rate or '',
            vital.respiratory_rate or '',
            vital.oxygen_saturation or ''
        ])

    # Write allergies
    writer.writerow([])
    writer.writerow(['Allergies'])
    writer.writerow(['Allergen', 'Severity', 'Reaction', 'Diagnosis Date'])
    for allergy in patient.allergies:
        writer.writerow([
            allergy.allergen,
            allergy.severity or '',
            allergy.reaction or '',
            allergy.diagnosis_date.strftime('%Y-%m-%d') if allergy.diagnosis_date else ''
        ])

    # Write medical history
    writer.writerow([])
    writer.writerow(['Medical History'])
    writer.writerow(['Condition', 'Diagnosis Date', 'Treatment', 'Status'])
    for history in patient.medical_history:
        writer.writerow([
            history.condition,
            history.diagnosis_date.strftime('%Y-%m-%d') if history.diagnosis_date else '',
            history.treatment or '',
            history.status or ''
        ])

    # Write prescriptions
    writer.writerow([])
    writer.writerow(['Prescriptions'])
    writer.writerow(['Date', 'Doctor', 'Diagnosis', 'Medications'])
    for prescription in patient.prescriptions:
        medications = '; '.join([
            f"{med.medication_name} ({med.dosage}, {med.frequency}, {med.duration})"
            for med in prescription.medications
        ])
        writer.writerow([
            prescription.date.strftime('%Y-%m-%d'),
            prescription.doctor.name,
            prescription.diagnosis,
            medications
        ])

    # Get the CSV data and create the response
    output = si.getvalue()
    si.close()

    # Create the response with CSV mimetype
    response = app.make_response(output)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=patient_{patient.id}_data_{datetime.now().strftime("%Y%m%d")}.csv'

    return response

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'doctor':
            flash('Access denied. Doctor privileges required.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/doctor/dashboard')
@login_required
@doctor_required
def doctor_dashboard():
    from models import Appointment, Prescription, LabTest
    from datetime import datetime, time

    # Get today's appointments
    today = datetime.now().date()
    today_appointments = Appointment.query.filter(
        Appointment.doctor_id == current_user.id,
        Appointment.date == today
    ).order_by(Appointment.time).all()

    # Get recent prescriptions
    recent_prescriptions = Prescription.query.filter_by(
        doctor_id=current_user.id
    ).order_by(Prescription.date.desc()).limit(5).all()

    # Get recent and pending lab tests
    recent_lab_tests = LabTest.query.filter_by(
        doctor_id=current_user.id
    ).order_by(LabTest.test_date.desc()).limit(5).all()

    pending_lab_tests = LabTest.query.filter_by(
        doctor_id=current_user.id,
        status='pending'
    ).all()

    return render_template('doctor_dashboard.html',
                         today_appointments=today_appointments,
                         recent_prescriptions=recent_prescriptions,
                         recent_lab_tests=recent_lab_tests,
                         pending_lab_tests=pending_lab_tests)

@app.route('/doctor/profile/update', methods=['POST'])
@login_required
@doctor_required
def update_doctor_profile():
    try:
        # Update basic information
        current_user.name = request.form['name']
        current_user.specialization = request.form.get('specialization')
        current_user.license_number = request.form.get('license_number')
        current_user.contact_number = request.form.get('contact_number')

        # Update schedule information
        working_days = request.form.getlist('working_days')
        current_user.working_days = ','.join(working_days) if working_days else None

        # Parse and set time fields
        for time_field in ['work_start_time', 'work_end_time', 'break_start_time', 'break_end_time']:
            time_value = request.form.get(time_field)
            if time_value:
                try:
                    # Convert string time to Time object
                    hours, minutes = map(int, time_value.split(':'))
                    setattr(current_user, time_field, time(hours, minutes))
                except ValueError:
                    setattr(current_user, time_field, None)
            else:
                setattr(current_user, time_field, None)

        # Update availability
        current_user.is_available = 'is_available' in request.form
        current_user.availability_notes = request.form.get('availability_notes')

        db.session.commit()
        flash('Profile updated successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating profile: {str(e)}')

    return redirect(url_for('doctor_dashboard'))

@app.route('/doctor/consultation/<int:appointment_id>', methods=['POST'])
@login_required
@doctor_required
def start_consultation(appointment_id):
    from models import Appointment
    appointment = Appointment.query.get_or_404(appointment_id)

    if appointment.doctor_id != current_user.id:
        flash('Access denied. This appointment belongs to another doctor.')
        return redirect(url_for('doctor_dashboard'))

    try:
        appointment.status = 'In Progress'
        db.session.commit()
        return redirect(url_for('patient_detail', id=appointment.patient_id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error starting consultation: {str(e)}')
        return redirect(url_for('doctor_dashboard'))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Administrator privileges required.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/roles')
@login_required
@admin_required
def role_management():
    from models import User
    users = User.query.all()
    return render_template('role_management.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    from models import User
    try:
        if User.query.filter_by(username=request.form['username']).first():
            flash('Username already exists')
            return redirect(url_for('role_management'))

        if User.query.filter_by(email=request.form['email']).first():
            flash('Email already exists')
            return redirect(url_for('role_management'))

        user = User(
            username=request.form['username'],
            email=request.form['email'],
            name=request.form['name'],
            role=request.form['role'],
            password_hash=generate_password_hash(request.form['password'])
        )
        db.session.add(user)
        db.session.commit()
        flash('User added successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding user: {str(e)}')
    return redirect(url_for('role_management'))

@app.route('/admin/users/update-role', methods=['POST'])
@login_required
@admin_required
def update_user_role():
    from models import User
    try:
        user = User.query.get_or_404(request.form['user_id'])
        if user.id == current_user.id:
            flash('You cannot change your own role')
            return redirect(url_for('role_management'))

        user.role = request.form['role']
        db.session.commit()
        flash('User role updated successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user role: {str(e)}')
    return redirect(url_for('role_management'))

@app.route('/api/wards/<int:ward_id>/available-beds')
@login_required
def get_available_beds(ward_id):
    from models import Bed
    beds = Bed.query.filter_by(ward_id=ward_id, occupied=False).all()
    return jsonify([{
        'id': bed.id,
        'number': bed.number
    } for bed in beds])

@app.route('/patients/add', methods=['POST'])
@login_required
def add_patient():
    from models import Patient
    try:
        patient = Patient(
            name=request.form['name'],
            age=request.form['age'],
            gender=request.form['gender'],
            contact=request.form['contact'],
            email=request.form.get('email'),
            blood_type=request.form.get('blood_type'),
            address=request.form.get('address')
        )
        db.session.add(patient)
        db.session.commit()
        flash('Patient added successfully')
        return redirect(url_for('patient_list'))
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding patient: {str(e)}')
        return redirect(url_for('patient_list'))


# Add these routes after the existing patient-related routes

@app.route('/patients/<int:id>/wellness-tip', methods=['GET'])
@login_required
def get_wellness_tip(id):
    from models import Patient
    from utils.wellness import generate_wellness_tip

    try:
        patient = Patient.query.get_or_404(id)
        tip_data = generate_wellness_tip(patient)
        return jsonify(tip_data)
    except Exception as e:
        logging.error(f"Error in wellness tip route: {str(e)}")
        return jsonify({
            'success': False,
            'tip': 'Error generating wellness tip. Please try again later.',
            'generated_at': datetime.utcnow()
        })

@app.route('/api/doctor-availability/<int:doctor_id>', methods=['GET'])
@login_required
def get_doctor_availability(doctor_id):
    from models import User, Appointment
    from datetime import datetime, timedelta

    doctor = User.query.get_or_404(doctor_id)
    date_str = request.args.get('date')

    try:
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format'}), 400

    # Get doctor's working hours
    if not doctor.work_start_time or not doctor.work_end_time:
        return jsonify({'error': 'Doctor has not set working hours'}), 400

    working_days = doctor.working_days.split(',') if doctor.working_days else []
    day_name = selected_date.strftime('%a')

    if day_name not in working_days:
        return jsonify({'error': 'Doctor is not available on this day'}), 400

    # Get existing appointments for the selected date
    existing_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date == selected_date
    ).all()

    booked_times = {apt.time.strftime('%H:%M') for apt in existing_appointments}

    # Generate available time slots (30-minute intervals)
    available_slots = []
    current_time = doctor.work_start_time

    while current_time <= doctor.work_end_time:
        # Skip break time if set
        if doctor.break_start_time and doctor.break_end_time:
            if not (doctor.break_start_time <= current_time <= doctor.break_end_time):
                time_str = current_time.strftime('%H:%M')
                if time_str not in booked_times:
                    available_slots.append(time_str)
        else:
            time_str = current_time.strftime('%H:%M')
            if time_str not in booked_times:
                available_slots.append(time_str)

        current_time = (datetime.combine(datetime.today(), current_time) + 
                       timedelta(minutes=30)).time()

    return jsonify({
        'doctor_name': doctor.name,
        'available_slots': available_slots,
        'working_hours': {
            'start': doctor.work_start_time.strftime('%H:%M'),
            'end': doctor.work_end_time.strftime('%H:%M'),
            'break_start': doctor.break_start_time.strftime('%H:%M') if doctor.break_start_time else None,
            'break_end': doctor.break_end_time.strftime('%H:%M') if doctor.break_end_time else None
        }
    })

@app.route('/appointments/schedule', methods=['POST'])
@login_required
def schedule_appointment():
    from models import Appointment, User
    try:
        doctor_id = request.form['doctor_id']
        patient_id = request.form['patient_id']
        date_str = request.form['date']
        time_str = request.form['time']

        # Validate doctor availability
        doctor = User.query.get_or_404(doctor_id)
        if not doctor.is_available:
            flash('Selected doctor is currently unavailable')
            return redirect(url_for('appointment_list'))

        # Convert strings to datetime objects
        appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        appointment_time = datetime.strptime(time_str, '%H:%M').time()

        # Check for existing appointments
        existing_appointment = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=appointment_date,
            time=appointment_time
        ).first()

        if existing_appointment:
            flash('This time slot is already booked')
            return redirect(url_for('appointment_list'))

        # Create new appointment
        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            date=appointment_date,
            time=appointment_time,
            status='Scheduled'
        )

        db.session.add(appointment)
        db.session.commit()
        flash('Appointment scheduled successfully')

    except Exception as e:
        db.session.rollback()
        flash(f'Error scheduling appointment: {str(e)}')

    return redirect(url_for('appointment_list'))

@app.route('/inventory')
@login_required
def inventory_list():
    from models import InventoryItem, InventoryBatch, InventoryTransaction

    # Get all inventory items
    items = InventoryItem.query.all()

    # Get items with stock below minimum level
    low_stock_items = [item for item in items if item.current_stock <= item.minimum_stock]

    # Get batches expiring in next 30 days
    expiring_soon = InventoryBatch.query\
        .filter(InventoryBatch.expiry_date <= (date.today() + timedelta(days=30)))\
        .filter(InventoryBatch.expiry_date >= date.today())\
        .all()

    # Get all suppliers
    from models import Supplier
    suppliers = Supplier.query.all()

    return render_template('inventory.html',
                         items=items,
                         low_stock_items=low_stock_items,
                         expiring_soon=expiring_soon,
                         suppliers=suppliers)

@app.route('/inventory/add', methods=['POST'])
@login_required
def add_inventory_item():
    from models import InventoryItem
    try:
        item = InventoryItem(
            name=request.form['name'],
            description=request.form.get('description'),
            category=request.form['category'],
            sku=request.form['sku'],
            unit=request.form['unit'],
            minimum_stock=int(request.form['minimum_stock']),
            maximum_stock=int(request.form['maximum_stock']),
            reorder_quantity=int(request.form['reorder_quantity']),
            supplier_id=request.form.get('supplier_id'),
            location=request.form.get('location'),
            unit_cost=request.form.get('unit_cost')
        )
        db.session.add(item)
        db.session.commit()
        flash('Inventory item added successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding inventory item: {str(e)}')
    return redirect(url_for('inventory_list'))

@app.route('/inventory/<int:id>/batch/add', methods=['POST'])
@login_required
def add_inventory_batch():
    from models import InventoryBatch, InventoryTransaction
    try:
        batch = InventoryBatch(
            inventory_item_id=id,
            batch_number=request.form['batch_number'],
            quantity=int(request.form['quantity']),
            manufacturing_date=datetime.strptime(request.form['manufacturing_date'], '%Y-%m-%d').date() if request.form.get('manufacturing_date') else None,
            expiry_date=datetime.strptime(request.form['expiry_date'], '%Y-%m-%d').date(),
            unit_cost=request.form.get('unit_cost'),
            remaining_quantity=int(request.form['quantity'])
        )
        db.session.add(batch)

        # Create a transaction record for the new batch
        transaction = InventoryTransaction(
            inventory_item_id=id,
            batch_id=batch.id,
            transaction_type='received',
            quantity=batch.quantity,
            reference_number=request.form.get('reference_number'),
            performed_by_id=current_user.id,
            notes=f'Initial batch receipt: {batch.batch_number}',
            unit_cost=batch.unit_cost
        )
        db.session.add(transaction)

        # Update item's current stock
        batch.item.current_stock += batch.quantity

        db.session.commit()
        flash('Inventory batch added successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding inventory batch: {str(e)}')
    return redirect(url_for('inventory_list'))

@app.route('/inventory/transaction/add', methods=['POST'])
@login_required
def add_inventory_transaction():
    from models import InventoryTransaction, InventoryItem, InventoryBatch
    try:
        item_id = request.form['inventory_item_id']
        quantity = int(request.form['quantity'])
        transaction_type = request.form['transaction_type']

        # Adjust quantity sign based on transaction type
        if transaction_type in ['consumed', 'expired']:
            quantity = -abs(quantity)

        transaction = InventoryTransaction(
            inventory_item_id=item_id,
            batch_id=request.form.get('batch_id'),
            transaction_type=transaction_type,
            quantity=quantity,
            reference_number=request.form.get('reference_number'),
            department=request.form.get('department'),
            performed_by_id=current_user.id,
            notes=request.form.get('notes')
        )

        # Update item's current stock
        item = InventoryItem.query.get(item_id)
        if item.current_stock + quantity < 0:
            raise ValueError('Insufficient stock')

        item.current_stock += quantity

        # Update batch remaining quantity if batch specified
        if transaction.batch_id:
            batch = InventoryBatch.query.get(transaction.batch_id)
            if batch.remaining_quantity + quantity < 0:
                raise ValueError('Insufficient batch quantity')
            batch.remaining_quantity += quantity

        db.session.add(transaction)
        db.session.commit()

        # Check if reorder needed
        if item.check_stock_status() == 'reorder':
            create_automated_order(item)

        flash('Transaction recorded successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error recording transaction: {str(e)}')
    return redirect(url_for('inventory_list'))

def create_automated_order(item):
    """Create an automated order for an item that needs reordering"""
    from models import AutomatedOrder
    try:
        order = AutomatedOrder(
            inventory_item_id=item.id,
            quantity=item.reorder_quantity,
            suggested_by='low_stock',
            notes=f'Automated reorder triggered. Current stock: {item.current_stock}'
        )
        db.session.add(order)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.error(f'Error creating automated order: {str(e)}')

@app.route('/inventory/analytics')
@login_required
def inventory_analytics():
    from models import InventoryItem, InventoryTransaction, InventoryBatch
    from sqlalchemy import func

    # Calculate total inventory value
    total_value = db.session.query(
        func.sum(InventoryItem.unit_cost * InventoryItem.current_stock)
    ).scalar() or 0

    # Get expiring items summary
    expiring_summary = len(InventoryBatch.query\
        .filter(InventoryBatch.expiry_date <= (date.today() + timedelta(days=90)))\
        .filter(InventoryBatch.expiry_date >= date.today())\
        .all())

    # Get consumption data for last 30 days
    thirty_days_ago = date.today() - timedelta(days=30)
    consumption_data = db.session.query(
        InventoryTransaction.inventory_item_id,
        func.sum(InventoryTransaction.quantity)
    ).filter(
        InventoryTransaction.transaction_type == 'consumed',
        InventoryTransaction.transaction_date >= thirty_days_ago
    ).group_by(
        InventoryTransaction.inventory_item_id
    ).all()

    return render_template('inventory_analytics.html',
                         total_value=total_value,
                         expiring_summary=expiring_summary,
                         consumption_data=consumption_data)

@app.route('/er/dashboard')
@login_required
def er_dashboard():
    from models import Ward, Admission, TRIAGE_COLORS
    from datetime import datetime

    # Get ER wards and their stats
    er_wards = Ward.query.filter_by(is_er=True).all()

    # Get ER statistics
    er_stats = {
        'total_patients': Admission.query.filter_by(status='active').count(),
        'available_beds': sum(ward.get_available_beds() for ward in er_wards),
        'waiting_patients': Admission.query.filter_by(status='waiting').count(),
        'avg_wait_time': db.session.query(
            func.avg(Admission.estimated_wait_time)
        ).filter_by(status='waiting').scalar() or 0
    }

    # Get triage category counts
    triage_counts = dict(
        db.session.query(
            Admission.triage_category,
            func.count(Admission.id)
        ).filter(
            Admission.status.in_(['active', 'waiting'])
        ).group_by(Admission.triage_category).all()
    )

    # Get queue ordered by priority
    queue = Admission.query.filter_by(status='waiting').order_by(
        Admission.priority_score,
        Admission.created_at
    ).all()

    # Update queue positions and wait times
    for position, admission in enumerate(queue, 1):
        admission.queue_position = position
        admission.calculate_estimated_wait_time()
    db.session.commit()

    return render_template('er_dashboard.html',
                         er_stats=er_stats,
                         er_wards=er_wards,
                         triage_counts=triage_counts,
                         queue=queue,
                         TRIAGE_COLORS=TRIAGE_COLORS,
                         now=datetime.utcnow())

@app.route('/er/patients/add', methods=['POST'])
@login_required
def add_er_patient():
    from models import Patient, Admission, Ward
    try:
        # Create new patient if they don't exist
        patient = Patient(
            name=request.form['name'],
            age=request.form['age'],
            gender=request.form['gender'],
            contact=request.form.get('contact', 'Unknown'),
            created_at=datetime.utcnow()
        )
        db.session.add(patient)
        db.session.flush()  # Get patient ID

        # Create admission record with triage information
        admission = Admission(
            patient_id=patient.id,
            admission_reason='Emergency',
            attending_doctor_id=current_user.id,
            triage_category=request.form['triage_category'],
            chief_complaint=request.form['chief_complaint'],
            initial_assessment=request.form.get('initial_assessment'),
            vital_signs={
                'temperature': request.form.get('temperature'),
                'blood_pressure': request.form.get('blood_pressure'),
                'heart_rate': request.form.get('heart_rate'),
                'oxygen_saturation': request.form.get('oxygen_saturation')
            }
        )

        db.session.add(admission)
        db.session.commit()

        # Update queue positions after adding new patient
        AdmissionQueue.update_queue_positions()

        flash('Patient added to ER queue successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding patient to ER: {str(e)}')

    return redirect(url_for('er_dashboard'))

@app.route('/er/admission/<int:id>/triage', methods=['POST'])
@login_required
def update_triage(id):
    from models import Admission
    try:
        admission = Admission.query.get_or_404(id)
        admission.triage_category = request.form['triage_category']
        admission.triage_notes = request.form.get('triage_notes')
        admission.update_priority_score()

        db.session.commit()

        # Update queue positions after triage change
        AdmissionQueue.update_queue_positions()

        flash('Triage category updated successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating triage: {str(e)}')

    return redirect(url_for('er_dashboard'))

@app.route('/inventory/suppliers')
@login_required
def supplier_list():
    from models import Supplier
    suppliers = Supplier.query.all()
    return render_template('inventory/suppliers.html', suppliers=suppliers)

@app.route('/inventory/suppliers/add', methods=['POST'])
@login_required
def add_supplier():
    from models import Supplier
    try:
        supplier = Supplier(
            name=request.form['name'],
            contact_person=request.form['contact_person'],
            email=request.form['email'],
            phone=request.form['phone'],
            address=request.form['address'],
            lead_time_days=int(request.form['lead_time_days']) if request.form.get('lead_time_days') else None
        )
        db.session.add(supplier)
        db.session.commit()
        flash('Supplier added successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error adding supplier: {str(e)}')
    return redirect(url_for('supplier_list'))

@app.route('/inventory/suppliers/<int:id>/update', methods=['POST'])
@login_required
def update_supplier(id):
    from models import Supplier
    try:
        supplier = Supplier.query.get_or_404(id)
        supplier.name = request.form['name']
        supplier.contact_person = request.form['contact_person']
        supplier.email = request.form['email']
        supplier.phone = request.form['phone']
        supplier.address = request.form['address']
        supplier.lead_time_days = int(request.form['lead_time_days']) if request.form.get('lead_time_days') else None
        db.session.commit()
        flash('Supplier updated successfully')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating supplier: {str(e)}')
    return redirect(url_for('supplier_list'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)