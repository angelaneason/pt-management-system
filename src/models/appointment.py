from src.models.user import db
from datetime import datetime

class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.id'), nullable=False)
    clinician_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    appointment_type = db.Column(db.String(20), default='individual')  # individual, group
    status = db.Column(db.String(20), default='scheduled')  # scheduled, completed, cancelled
    notes = db.Column(db.Text)
    recurrence_pattern = db.Column(db.String(50))  # daily, weekly, monthly, etc.
    recurrence_end_date = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    patient = db.relationship('Patient', backref='patient_appointments')
    clinician = db.relationship('User', backref='clinician_appointments')

    def __repr__(self):
        return f'<Appointment {self.id} - {self.patient.name if self.patient else "Unknown"} with {self.clinician.username if self.clinician else "Unknown"}>'

    def to_dict(self):
        return {
            'id': self.id,
            'patient_id': self.patient_id,
            'patient_name': self.patient.name if self.patient else None,
            'clinician_id': self.clinician_id,
            'clinician_name': self.clinician.username if self.clinician else None,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'appointment_type': self.appointment_type,
            'status': self.status,
            'notes': self.notes,
            'recurrence_pattern': self.recurrence_pattern,
            'recurrence_end_date': self.recurrence_end_date.isoformat() if self.recurrence_end_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

