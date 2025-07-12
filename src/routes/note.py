from flask import Blueprint, jsonify, request, session
from src.models.note import Note, NoteTemplate
from src.models.user import User, db
from src.routes.auth import login_required, admin_required

note_bp = Blueprint('note', __name__)

@note_bp.route('/appointments/<int:appointment_id>/notes', methods=['POST'])
@login_required
def create_note(appointment_id):
    try:
        data = request.json
        user = User.query.get(session['user_id'])
        
        # Validate required fields
        if 'content' not in data:
            return jsonify({'error': 'Content is required'}), 400
        
        note = Note(
            appointment_id=appointment_id,
            clinician_id=user.id,
            content=data['content'],
            note_type=data.get('note_type', 'visit'),
            template_id=data.get('template_id')
        )
        
        db.session.add(note)
        db.session.commit()
        return jsonify(note.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/appointments/<int:appointment_id>/notes', methods=['GET'])
@login_required
def get_appointment_notes(appointment_id):
    try:
        user = User.query.get(session['user_id'])
        
        # Base query
        query = Note.query.filter_by(appointment_id=appointment_id)
        
        # Role-based filtering
        if user.role == 'Clinician':
            # Clinicians can only see notes for appointments they're assigned to
            from src.models.appointment import Appointment
            appointment = Appointment.query.get_or_404(appointment_id)
            if appointment.clinician_id != user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        notes = query.order_by(Note.created_at).all()
        return jsonify([note.to_dict() for note in notes])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
@login_required
def update_note(note_id):
    try:
        note = Note.query.get_or_404(note_id)
        user = User.query.get(session['user_id'])
        data = request.json
        
        # Check permissions - only the clinician who created the note can edit it
        if note.clinician_id != user.id and user.role != 'Admin':
            return jsonify({'error': 'Access denied'}), 403
        
        # Update note fields
        note.content = data.get('content', note.content)
        note.note_type = data.get('note_type', note.note_type)
        note.template_id = data.get('template_id', note.template_id)
        
        db.session.commit()
        return jsonify(note.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
@login_required
def delete_note(note_id):
    try:
        note = Note.query.get_or_404(note_id)
        user = User.query.get(session['user_id'])
        
        # Check permissions
        if note.clinician_id != user.id and user.role != 'Admin':
            return jsonify({'error': 'Access denied'}), 403
        
        db.session.delete(note)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/patients/<int:patient_id>/notes', methods=['GET'])
@login_required
def get_patient_notes(patient_id):
    try:
        user = User.query.get(session['user_id'])
        
        # Get all notes for appointments with this patient
        from src.models.appointment import Appointment
        
        # Base query - join notes with appointments to filter by patient
        query = db.session.query(Note).join(Appointment).filter(Appointment.patient_id == patient_id)
        
        # Role-based filtering
        if user.role == 'Clinician':
            # Clinicians can only see notes for their own appointments
            query = query.filter(Appointment.clinician_id == user.id)
        
        notes = query.order_by(Note.created_at.desc()).all()
        return jsonify([note.to_dict() for note in notes])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@note_bp.route('/appointments/<int:appointment_id>/notes/export/pdf', methods=['GET'])
@login_required
def export_notes_pdf(appointment_id):
    try:
        user = User.query.get(session['user_id'])
        
        # Check permissions
        from src.models.appointment import Appointment
        appointment = Appointment.query.get_or_404(appointment_id)
        
        if user.role == 'Clinician' and appointment.clinician_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get notes for the appointment
        notes = Note.query.filter_by(appointment_id=appointment_id).order_by(Note.created_at).all()
        
        # In a real implementation, this would generate a PDF
        # For now, we'll return the notes data with a message
        return jsonify({
            'message': 'PDF export functionality would be implemented here',
            'appointment': appointment.to_dict(),
            'notes': [note.to_dict() for note in notes]
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Note Templates
@note_bp.route('/notes/templates', methods=['GET'])
@login_required
def get_note_templates():
    try:
        templates = NoteTemplate.query.filter_by(is_active=True).all()
        return jsonify([template.to_dict() for template in templates])
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/templates', methods=['POST'])
@admin_required
def create_note_template():
    try:
        data = request.json
        user = User.query.get(session['user_id'])
        
        # Validate required fields
        required_fields = ['name', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        template = NoteTemplate(
            name=data['name'],
            content=data['content'],
            category=data.get('category', ''),
            created_by=user.id
        )
        
        db.session.add(template)
        db.session.commit()
        return jsonify(template.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/templates/<int:template_id>', methods=['PUT'])
@admin_required
def update_note_template(template_id):
    try:
        template = NoteTemplate.query.get_or_404(template_id)
        data = request.json
        
        # Update template fields
        template.name = data.get('name', template.name)
        template.content = data.get('content', template.content)
        template.category = data.get('category', template.category)
        template.is_active = data.get('is_active', template.is_active)
        
        db.session.commit()
        return jsonify(template.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@note_bp.route('/notes/templates/<int:template_id>', methods=['DELETE'])
@admin_required
def delete_note_template(template_id):
    try:
        template = NoteTemplate.query.get_or_404(template_id)
        # Soft delete - mark as inactive
        template.is_active = False
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

