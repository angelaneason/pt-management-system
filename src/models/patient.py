"""
Patient model for tenant-specific data in the Physical Therapy Management System.

This model exists within each tenant schema and represents patients receiving
physical therapy services from the practice.
"""

from src.models.public import db
from datetime import datetime, date

class Patient(db.Model):
    """
    Patient records within a tenant's practice.
    Contains comprehensive patient information for physical therapy services.
    """
    id = db.Column(db.Integer, primary_key=True)
    
    # Basic demographic information
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    middle_name = db.Column(db.String(50))
    preferred_name = db.Column(db.String(50))
    
    # Personal identifiers
    medical_record_number = db.Column(db.String(50), unique=True)
    ssn_last_four = db.Column(db.String(4))  # Only store last 4 digits for privacy
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    
    # Contact information
    email = db.Column(db.String(120))
    phone_primary = db.Column(db.String(20))
    phone_secondary = db.Column(db.String(20))
    preferred_contact_method = db.Column(db.String(20), default='Phone')
    
    # Address information
    address_line1 = db.Column(db.String(200))
    address_line2 = db.Column(db.String(200))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    zip_code = db.Column(db.String(10))
    country = db.Column(db.String(50), default='USA')
    
    # Emergency contact
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_relationship = db.Column(db.String(50))
    emergency_contact_phone = db.Column(db.String(20))
    
    # Insurance information
    primary_insurance = db.Column(db.String(100))
    primary_insurance_id = db.Column(db.String(50))
    primary_insurance_group = db.Column(db.String(50))
    secondary_insurance = db.Column(db.String(100))
    secondary_insurance_id = db.Column(db.String(50))
    
    # Medical information
    primary_diagnosis = db.Column(db.String(200))
    secondary_diagnoses = db.Column(db.JSON)  # Array of additional diagnoses
    icd10_codes = db.Column(db.JSON)  # Array of ICD-10 codes
    referring_physician = db.Column(db.String(100))
    referring_physician_npi = db.Column(db.String(20))
    
    # Physical therapy specific
    therapy_start_date = db.Column(db.Date)
    therapy_end_date = db.Column(db.Date)
    frequency_per_week = db.Column(db.Integer, default=2)
    total_visits_authorized = db.Column(db.Integer)
    visits_completed = db.Column(db.Integer, default=0)
    visits_remaining = db.Column(db.Integer)
    
    # Clinical information
    chief_complaint = db.Column(db.Text)
    medical_history = db.Column(db.Text)
    surgical_history = db.Column(db.Text)
    medications = db.Column(db.JSON)  # Array of current medications
    allergies = db.Column(db.JSON)  # Array of allergies
    precautions = db.Column(db.Text)
    contraindications = db.Column(db.Text)
    
    # Functional status
    functional_limitations = db.Column(db.Text)
    goals_short_term = db.Column(db.JSON)  # Array of short-term goals
    goals_long_term = db.Column(db.JSON)  # Array of long-term goals
    prior_level_of_function = db.Column(db.Text)
    
    # Assessment scores
    initial_pain_score = db.Column(db.Integer)  # 0-10 scale
    current_pain_score = db.Column(db.Integer)  # 0-10 scale
    outcome_measures = db.Column(db.JSON)  # Various standardized assessments
    
    # Care coordination
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'))
    primary_therapist_id = db.Column(db.Integer)  # References user_profile.user_id
    care_team = db.Column(db.JSON)  # Array of user IDs involved in care
    
    # Scheduling preferences
    preferred_appointment_days = db.Column(db.JSON)  # Array of preferred days
    preferred_appointment_times = db.Column(db.JSON)  # Array of preferred time slots
    scheduling_notes = db.Column(db.Text)
    
    # Communication preferences
    language_preference = db.Column(db.String(50), default='English')
    interpreter_needed = db.Column(db.Boolean, default=False)
    communication_notes = db.Column(db.Text)
    
    # Billing and financial
    copay_amount = db.Column(db.Float)
    deductible_met = db.Column(db.Boolean, default=False)
    financial_responsibility = db.Column(db.Text)
    payment_plan = db.Column(db.String(50))
    
    # Status and workflow
    status = db.Column(db.String(50), default='Active')  # Active, Discharged, On Hold, etc.
    discharge_date = db.Column(db.Date)
    discharge_reason = db.Column(db.String(100))
    discharge_summary = db.Column(db.Text)
    
    # Quality and outcomes
    satisfaction_score = db.Column(db.Integer)  # 1-5 scale
    outcome_achieved = db.Column(db.Boolean)
    readmission_risk = db.Column(db.String(20))  # Low, Medium, High
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer)  # User ID who created this patient
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_visit_date = db.Column(db.Date)
    next_appointment_date = db.Column(db.Date)
    
    # Relationships
    client = db.relationship('Client', back_populates='patients')
    appointments = db.relationship('Appointment', back_populates='patient', lazy='dynamic')
    notes = db.relationship('Note', back_populates='patient', lazy='dynamic')
    
    def __repr__(self):
        return f'<Patient {self.first_name} {self.last_name}>'
    
    @property
    def full_name(self):
        """Get patient's full name"""
        name_parts = [self.first_name]
        if self.middle_name:
            name_parts.append(self.middle_name)
        name_parts.append(self.last_name)
        return ' '.join(name_parts)
    
    @property
    def display_name(self):
        """Get patient's display name (preferred name if available)"""
        if self.preferred_name:
            return f"{self.preferred_name} {self.last_name}"
        return self.full_name
    
    @property
    def age(self):
        """Calculate patient's current age"""
        if self.date_of_birth:
            today = date.today()
            return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        return None
    
    def get_full_address(self):
        """Get formatted full address"""
        address_parts = []
        if self.address_line1:
            address_parts.append(self.address_line1)
        if self.address_line2:
            address_parts.append(self.address_line2)
        if self.city:
            city_state_zip = self.city
            if self.state:
                city_state_zip += f", {self.state}"
            if self.zip_code:
                city_state_zip += f" {self.zip_code}"
            address_parts.append(city_state_zip)
        return "\n".join(address_parts)
    
    def update_visit_counts(self):
        """Update visit counts based on completed appointments"""
        completed_appointments = self.appointments.filter_by(status='Completed').count()
        self.visits_completed = completed_appointments
        if self.total_visits_authorized:
            self.visits_remaining = max(0, self.total_visits_authorized - self.visits_completed)
    
    def get_recent_appointments(self, days=30):
        """Get recent appointments"""
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        return self.appointments.filter(Appointment.appointment_date >= cutoff_date).all()
    
    def get_upcoming_appointments(self):
        """Get upcoming appointments"""
        return self.appointments.filter(Appointment.appointment_date >= datetime.utcnow()).order_by(Appointment.appointment_date).all()
    
    def get_latest_note(self):
        """Get the most recent clinical note"""
        return self.notes.order_by(Note.created_at.desc()).first()
    
    def is_due_for_reassessment(self, days=30):
        """Check if patient is due for reassessment"""
        if self.last_visit_date:
            from datetime import timedelta
            return (date.today() - self.last_visit_date).days >= days
        return True
    
    def calculate_progress_percentage(self):
        """Calculate therapy progress as percentage"""
        if self.total_visits_authorized and self.visits_completed:
            return min(100, (self.visits_completed / self.total_visits_authorized) * 100)
        return 0
    
    def to_dict(self, include_relationships=False):
        data = {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'middle_name': self.middle_name,
            'preferred_name': self.preferred_name,
            'full_name': self.full_name,
            'display_name': self.display_name,
            'medical_record_number': self.medical_record_number,
            'ssn_last_four': self.ssn_last_four,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'age': self.age,
            'gender': self.gender,
            'email': self.email,
            'phone_primary': self.phone_primary,
            'phone_secondary': self.phone_secondary,
            'preferred_contact_method': self.preferred_contact_method,
            'address_line1': self.address_line1,
            'address_line2': self.address_line2,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'country': self.country,
            'full_address': self.get_full_address(),
            'emergency_contact_name': self.emergency_contact_name,
            'emergency_contact_relationship': self.emergency_contact_relationship,
            'emergency_contact_phone': self.emergency_contact_phone,
            'primary_insurance': self.primary_insurance,
            'primary_insurance_id': self.primary_insurance_id,
            'primary_insurance_group': self.primary_insurance_group,
            'secondary_insurance': self.secondary_insurance,
            'secondary_insurance_id': self.secondary_insurance_id,
            'primary_diagnosis': self.primary_diagnosis,
            'secondary_diagnoses': self.secondary_diagnoses,
            'icd10_codes': self.icd10_codes,
            'referring_physician': self.referring_physician,
            'referring_physician_npi': self.referring_physician_npi,
            'therapy_start_date': self.therapy_start_date.isoformat() if self.therapy_start_date else None,
            'therapy_end_date': self.therapy_end_date.isoformat() if self.therapy_end_date else None,
            'frequency_per_week': self.frequency_per_week,
            'total_visits_authorized': self.total_visits_authorized,
            'visits_completed': self.visits_completed,
            'visits_remaining': self.visits_remaining,
            'chief_complaint': self.chief_complaint,
            'medical_history': self.medical_history,
            'surgical_history': self.surgical_history,
            'medications': self.medications,
            'allergies': self.allergies,
            'precautions': self.precautions,
            'contraindications': self.contraindications,
            'functional_limitations': self.functional_limitations,
            'goals_short_term': self.goals_short_term,
            'goals_long_term': self.goals_long_term,
            'prior_level_of_function': self.prior_level_of_function,
            'initial_pain_score': self.initial_pain_score,
            'current_pain_score': self.current_pain_score,
            'outcome_measures': self.outcome_measures,
            'client_id': self.client_id,
            'primary_therapist_id': self.primary_therapist_id,
            'care_team': self.care_team,
            'preferred_appointment_days': self.preferred_appointment_days,
            'preferred_appointment_times': self.preferred_appointment_times,
            'scheduling_notes': self.scheduling_notes,
            'language_preference': self.language_preference,
            'interpreter_needed': self.interpreter_needed,
            'communication_notes': self.communication_notes,
            'copay_amount': self.copay_amount,
            'deductible_met': self.deductible_met,
            'financial_responsibility': self.financial_responsibility,
            'payment_plan': self.payment_plan,
            'status': self.status,
            'discharge_date': self.discharge_date.isoformat() if self.discharge_date else None,
            'discharge_reason': self.discharge_reason,
            'discharge_summary': self.discharge_summary,
            'satisfaction_score': self.satisfaction_score,
            'outcome_achieved': self.outcome_achieved,
            'readmission_risk': self.readmission_risk,
            'is_active': self.is_active,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_visit_date': self.last_visit_date.isoformat() if self.last_visit_date else None,
            'next_appointment_date': self.next_appointment_date.isoformat() if self.next_appointment_date else None,
            'progress_percentage': self.calculate_progress_percentage()
        }
        
        if include_relationships:
            data['client'] = self.client.to_dict() if self.client else None
            data['recent_appointments'] = [apt.to_dict() for apt in self.get_recent_appointments()]
            data['upcoming_appointments'] = [apt.to_dict() for apt in self.get_upcoming_appointments()]
            data['latest_note'] = self.get_latest_note().to_dict() if self.get_latest_note() else None
        
        return data

