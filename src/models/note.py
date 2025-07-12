from src.models.user import db
from datetime import datetime

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    clinician_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    note_type = db.Column(db.String(20), default='visit')  # pre-visit, visit, post-visit
    template_id = db.Column(db.Integer, db.ForeignKey('note_template.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    appointment = db.relationship('Appointment', backref='appointment_notes')
    clinician = db.relationship('User', backref='clinician_notes')
    template = db.relationship('NoteTemplate', backref='template_notes')

    def __repr__(self):
        return f'<Note {self.id} - {self.note_type}>'

    def to_dict(self):
        return {
            'id': self.id,
            'appointment_id': self.appointment_id,
            'clinician_id': self.clinician_id,
            'clinician_name': self.clinician.username if self.clinician else None,
            'content': self.content,
            'note_type': self.note_type,
            'template_id': self.template_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class NoteTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50))  # assessment, treatment, progress, etc.
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship
    creator = db.relationship('User', backref='created_note_templates')

    def __repr__(self):
        return f'<NoteTemplate {self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'content': self.content,
            'category': self.category,
            'created_by': self.created_by,
            'creator_name': self.creator.username if self.creator else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active
        }

