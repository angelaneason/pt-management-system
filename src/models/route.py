from src.models.user import db
from datetime import datetime
import json

class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    clinician_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    route_date = db.Column(db.Date, nullable=False)
    optimized_path = db.Column(db.Text)  # JSON string containing route data
    total_distance = db.Column(db.Float)  # in miles/km
    estimated_duration = db.Column(db.Integer)  # in minutes
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    clinician = db.relationship('User', backref='clinician_routes')

    def __repr__(self):
        return f'<Route {self.id} - {self.clinician.username if self.clinician else "Unknown"} on {self.route_date}>'

    def set_optimized_path(self, path_data):
        """Store route path data as JSON string"""
        self.optimized_path = json.dumps(path_data)

    def get_optimized_path(self):
        """Retrieve route path data from JSON string"""
        if self.optimized_path:
            return json.loads(self.optimized_path)
        return None

    def to_dict(self):
        return {
            'id': self.id,
            'clinician_id': self.clinician_id,
            'clinician_name': self.clinician.username if self.clinician else None,
            'route_date': self.route_date.isoformat() if self.route_date else None,
            'optimized_path': self.get_optimized_path(),
            'total_distance': self.total_distance,
            'estimated_duration': self.estimated_duration,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class RouteStop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    stop_order = db.Column(db.Integer, nullable=False)
    visit_notes = db.Column(db.Text)
    arrival_time = db.Column(db.DateTime)
    departure_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending')  # pending, in-progress, completed, skipped

    # Relationships
    route = db.relationship('Route', backref='route_stops')
    appointment = db.relationship('Appointment', backref='appointment_route_stops')

    def __repr__(self):
        return f'<RouteStop {self.id} - Stop {self.stop_order}>'

    def to_dict(self):
        return {
            'id': self.id,
            'route_id': self.route_id,
            'appointment_id': self.appointment_id,
            'stop_order': self.stop_order,
            'visit_notes': self.visit_notes,
            'arrival_time': self.arrival_time.isoformat() if self.arrival_time else None,
            'departure_time': self.departure_time.isoformat() if self.departure_time else None,
            'status': self.status,
            'patient_name': self.appointment.patient.name if self.appointment and self.appointment.patient else None,
            'patient_address': self.appointment.patient.address if self.appointment and self.appointment.patient else None,
            'patient_phone': self.appointment.patient.phone if self.appointment and self.appointment.patient else None
        }

