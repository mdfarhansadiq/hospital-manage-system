from extensions import db
from flask_login import UserMixin
from datetime import datetime, date, timedelta

# Update Priority Queue Constants
PRIORITY_LEVELS = {
    'immediate': 1,    # Red - Immediate life-threatening
    'emergency': 2,    # Orange - Very urgent
    'urgent': 3,       # Yellow - Urgent
    'standard': 4,     # Green - Standard
    'non_urgent': 5    # Blue - Non-urgent
}

TRIAGE_COLORS = {
    'immediate': 'red',
    'emergency': 'orange',
    'urgent': 'yellow',
    'standard': 'green',
    'non_urgent': 'blue'
}

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationship with doctors (User model)
    doctors = db.relationship('User', backref='department', lazy=True)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('department.id'))
    # Doctor specific fields
    specialization = db.Column(db.String(100))
    license_number = db.Column(db.String(50))
    contact_number = db.Column(db.String(20))
    # New schedule fields
    working_days = db.Column(db.String(100))  # Stored as comma-separated days (e.g., "Mon,Tue,Wed")
    work_start_time = db.Column(db.Time)
    work_end_time = db.Column(db.Time)
    break_start_time = db.Column(db.Time)
    break_end_time = db.Column(db.Time)
    is_available = db.Column(db.Boolean, default=True)
    availability_notes = db.Column(db.Text)
    # Relationships
    appointments = db.relationship('Appointment', backref='doctor', lazy=True)
    prescriptions = db.relationship('Prescription', backref='doctor', lazy=True)
    lab_tests = db.relationship('LabTest', backref='doctor', lazy=True)
    managed_admissions = db.relationship('Admission', backref='attending_doctor', lazy=True)
    inventory_transactions = db.relationship('InventoryTransaction', 
                                           backref='performed_by', 
                                           lazy=True,
                                           foreign_keys='InventoryTransaction.performed_by_id')
    approved_orders = db.relationship('AutomatedOrder', 
                                     backref='approved_by', 
                                     lazy=True,
                                     foreign_keys='AutomatedOrder.approved_by_id')


class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(1), nullable=False)
    contact = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    blood_type = db.Column(db.String(5))
    date_of_birth = db.Column(db.Date)
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_number = db.Column(db.String(20))
    insurance_provider = db.Column(db.String(100))
    insurance_number = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships
    appointments = db.relationship('Appointment', backref='patient', lazy=True)
    bed = db.relationship('Bed', backref='patient', uselist=False)
    prescriptions = db.relationship('Prescription', backref='patient', lazy=True)
    lab_tests = db.relationship('LabTest', backref='patient', lazy=True)
    medical_history = db.relationship('MedicalHistory', backref='patient', lazy=True)
    allergies = db.relationship('PatientAllergy', backref='patient', lazy=True)
    vital_signs = db.relationship('VitalSign', backref='patient', lazy=True)
    documents = db.relationship('PatientDocument', backref='patient', lazy=True)
    admissions = db.relationship('Admission', backref='patient', lazy=True)
    current_admission = db.relationship('Admission', 
                                        primaryjoin="and_(Patient.id==Admission.patient_id, "
                                                   "Admission.status=='active')",
                                        uselist=False)


class Ward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    ward_type = db.Column(db.String(20), nullable=False)  # emergency, general, icu, etc.
    floor = db.Column(db.Integer, nullable=False)
    is_er = db.Column(db.Boolean, default=False)  # Identifies Emergency Room wards
    beds = db.relationship('Bed', backref='ward', lazy=True)

    def get_available_beds(self):
        """Get number of available beds in the ward"""
        return len([bed for bed in self.beds if not bed.occupied])

    def get_next_available_bed(self):
        """Get the next available bed in the ward"""
        return next((bed for bed in self.beds if not bed.occupied), None)

class Bed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ward_id = db.Column(db.Integer, db.ForeignKey('ward.id'), nullable=False)
    number = db.Column(db.Integer, nullable=False)
    occupied = db.Column(db.Boolean, default=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=True)
    status = db.Column(db.String(20), default='available')  # available, occupied, maintenance, reserved
    equipment = db.Column(db.String(200))  # Comma-separated list of available equipment
    notes = db.Column(db.Text)
    last_cleaned = db.Column(db.DateTime)
    # Update relationship to use back_populates
    admission = db.relationship('Admission', back_populates='bed', uselist=False)

class Admission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    bed_id = db.Column(db.Integer, db.ForeignKey('bed.id'), nullable=True)
    admission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    discharge_date = db.Column(db.DateTime)
    admission_reason = db.Column(db.Text, nullable=False)
    admission_notes = db.Column(db.Text)
    attending_doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='waiting')  # waiting, active, discharged
    priority_level = db.Column(db.String(20), nullable=False, default='standard')
    priority_score = db.Column(db.Integer, nullable=False, default=4)  # Lower number = higher priority
    triage_category = db.Column(db.String(20))  # immediate, emergency, urgent, standard, non_urgent
    triage_notes = db.Column(db.Text)
    initial_assessment = db.Column(db.Text)
    vital_signs = db.Column(db.JSON)  # Store initial vital signs
    chief_complaint = db.Column(db.Text)
    estimated_wait_time = db.Column(db.Integer)  # in minutes
    actual_wait_time = db.Column(db.Integer)  # in minutes
    queue_position = db.Column(db.Integer)  # Position in the waiting list
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Update relationship to use back_populates
    bed = db.relationship('Bed', back_populates='admission', uselist=False)

    def update_priority_score(self):
        """Update priority score based on various factors"""
        base_score = PRIORITY_LEVELS.get(self.triage_category, 4)
        wait_time = (datetime.utcnow() - self.created_at).total_seconds() / 3600  # hours
        # Priority increases (score decreases) with wait time
        time_factor = min(wait_time / 2, 3)  # Max 3 point boost from wait time
        self.priority_score = max(1, base_score - time_factor)

    def calculate_estimated_wait_time(self, average_treatment_time=30):
        """Calculate estimated wait time based on queue position and priority"""
        if self.status != 'waiting':
            return 0

        # Get all waiting patients with higher priority
        higher_priority = Admission.query.filter(
            Admission.status == 'waiting',
            Admission.priority_score < self.priority_score
        ).count()

        # Calculate base wait time
        self.estimated_wait_time = (higher_priority + 1) * average_treatment_time
        return self.estimated_wait_time

class AdmissionQueue(db.Model):
    """Model to manage the admission waiting list"""
    id = db.Column(db.Integer, primary_key=True)
    admission_id = db.Column(db.Integer, db.ForeignKey('admission.id'), nullable=False, unique=True)
    ward_type_needed = db.Column(db.String(20), nullable=False)
    special_requirements = db.Column(db.Text)
    last_priority_update = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationships
    admission = db.relationship('Admission', backref='queue_entry', uselist=False)

    def __repr__(self):
        return f'<AdmissionQueue {self.id} - Admission {self.admission_id}>'

    @staticmethod
    def update_queue_positions():
        """Update queue positions based on priority scores"""
        waiting_admissions = (Admission.query
                            .filter_by(status='waiting')
                            .order_by(Admission.priority_score)
                            .all())

        for position, admission in enumerate(waiting_admissions, 1):
            admission.queue_position = position
            admission.calculate_estimated_wait_time()


class MedicalHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    condition = db.Column(db.String(200), nullable=False)
    diagnosis_date = db.Column(db.Date)
    treatment = db.Column(db.Text)
    status = db.Column(db.String(20))  # active, resolved, chronic
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PatientAllergy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    allergen = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20))  # mild, moderate, severe
    reaction = db.Column(db.Text)
    diagnosis_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VitalSign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    temperature = db.Column(db.Float)
    blood_pressure_systolic = db.Column(db.Integer)
    blood_pressure_diastolic = db.Column(db.Integer)
    heart_rate = db.Column(db.Integer)
    respiratory_rate = db.Column(db.Integer)
    oxygen_saturation = db.Column(db.Integer)
    measured_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    notes = db.Column(db.Text)
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class PatientDocument(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # lab_report, prescription, imaging, consent_form
    title = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Prescription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    diagnosis = db.Column(db.Text, nullable=False)
    medications = db.relationship('PrescriptionMedication', backref='prescription', lazy=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='active')

class PrescriptionMedication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prescription_id = db.Column(db.Integer, db.ForeignKey('prescription.id'), nullable=False)
    medication_name = db.Column(db.String(100), nullable=False)
    dosage = db.Column(db.String(50), nullable=False)
    frequency = db.Column(db.String(50), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    instructions = db.Column(db.Text)

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    duration = db.Column(db.Integer, default=30)  # Duration in minutes
    status = db.Column(db.String(20), nullable=False, default='Scheduled')
    calendar_event_id = db.Column(db.String(100))  # Google Calendar event ID
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def start_time(self):
        """Combine date and time into datetime object"""
        return datetime.combine(self.date, self.time)

    @property
    def end_time(self):
        """Calculate end time based on duration"""
        return self.start_time + timedelta(minutes=self.duration)

    def sync_with_calendar(self, calendar_service):
        """Sync appointment with Google Calendar"""
        from utils.google_calendar import create_calendar_event, update_calendar_event

        if not self.calendar_event_id:
            # Create new calendar event
            event = create_calendar_event(calendar_service, self)
            self.calendar_event_id = event['id']
        else:
            # Update existing calendar event
            update_calendar_event(calendar_service, self.calendar_event_id, self)


class LabTestCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    tests = db.relationship('LabTest', backref='category', lazy=True)

class LabTest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('lab_test_category.id'), nullable=False)
    test_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    priority = db.Column(db.String(20), default='routine')  # routine, urgent, emergency
    notes = db.Column(db.Text)
    results = db.relationship('LabTestResult', backref='test', lazy=True)

class LabTestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('lab_test.id'), nullable=False)
    parameter_name = db.Column(db.String(100), nullable=False)
    value = db.Column(db.String(100), nullable=False)
    unit = db.Column(db.String(50))
    reference_range = db.Column(db.String(100))
    is_abnormal = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    lead_time_days = db.Column(db.Integer)  # Typical delivery time in days
    items = db.relationship('InventoryItem', backref='supplier', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class InventoryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), nullable=False)  # e.g., medication, supplies, equipment
    sku = db.Column(db.String(50), unique=True)  # Stock Keeping Unit
    unit = db.Column(db.String(20), nullable=False)  # e.g., pieces, boxes, ml
    current_stock = db.Column(db.Integer, default=0)
    minimum_stock = db.Column(db.Integer, nullable=False)  # Reorder point
    maximum_stock = db.Column(db.Integer, nullable=False)  # Maximum inventory level
    reorder_quantity = db.Column(db.Integer, nullable=False)  # Standard order quantity
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    location = db.Column(db.String(100))  # Storage location
    unit_cost = db.Column(db.Numeric(10, 2))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Relationships
    transactions = db.relationship('InventoryTransaction', backref='item', lazy=True)
    batches = db.relationship('InventoryBatch', backref='item', lazy=True)

    def check_stock_status(self):
        """Check if item needs reordering"""
        if self.current_stock <= self.minimum_stock:
            return 'reorder'
        return 'ok'

class InventoryBatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    batch_number = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    manufacturing_date = db.Column(db.Date)
    expiry_date = db.Column(db.Date, nullable=False)
    unit_cost = db.Column(db.Numeric(10, 2))
    remaining_quantity = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    def is_expired(self):
        """Check if batch is expired"""
        return self.expiry_date <= date.today()

    def expires_soon(self, days=30):
        """Check if batch expires within specified days"""
        return (self.expiry_date - date.today()).days <= days

class InventoryTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    batch_id = db.Column(db.Integer, db.ForeignKey('inventory_batch.id'))
    transaction_type = db.Column(db.String(20), nullable=False)  # received, consumed, adjusted, expired
    quantity = db.Column(db.Integer, nullable=False)  # Positive for in, negative for out
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    reference_number = db.Column(db.String(50))  # PO number or requisition number
    department = db.Column(db.String(50))  # Department where used
    performed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text)
    unit_cost = db.Column(db.Numeric(10, 2))  # Cost at time of transaction

class AutomatedOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventory_item_id = db.Column(db.Integer, db.ForeignKey('inventory_item.id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, ordered, received
    suggested_by = db.Column(db.String(50))  # low_stock, expiry, usage_pattern
    approved_by_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Add after the existing models
class Ambulance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_number = db.Column(db.String(20), unique=True, nullable=False)
    vehicle_type = db.Column(db.String(50), nullable=False)  # Basic, Advanced Life Support, etc.
    status = db.Column(db.String(20), default='available')  # available, busy, maintenance
    current_location = db.Column(db.String(200))
    last_location_update = db.Column(db.DateTime, default=datetime.utcnow)
    capacity = db.Column(db.Integer, default=2)  # Number of patients it can carry
    equipment = db.Column(db.Text)  # List of available equipment
    staff_assigned = db.relationship('User', secondary='ambulance_staff', backref='ambulances')
    maintenance_due_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Association table for ambulance staff assignments
ambulance_staff = db.Table('ambulance_staff',
    db.Column('ambulance_id', db.Integer, db.ForeignKey('ambulance.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

class AmbulanceDispatch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ambulance_id = db.Column(db.Integer, db.ForeignKey('ambulance.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'))
    dispatch_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    pickup_location = db.Column(db.String(200), nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    priority_level = db.Column(db.String(20), nullable=False)  # emergency, urgent, non-urgent
    status = db.Column(db.String(20), default='dispatched')  # dispatched, completed, cancelled
    completion_time = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    dispatched_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    ambulance = db.relationship('Ambulance', backref='dispatches')
    patient = db.relationship('Patient', backref='ambulance_dispatches')
    dispatched_by = db.relationship('User', backref='dispatches')