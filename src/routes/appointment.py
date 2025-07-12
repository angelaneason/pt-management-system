from flask import Blueprint, jsonify, request, session
from src.models.appointment import Appointment
from src.models.user import User, db
from src.routes.auth import login_required, admin_required
from datetime import datetime, timedelta
import dateutil.parser

appointment_bp = Blueprint('appointment', __name__)

@appointment_bp.route('/appointments', methods=['GET'])
@login_required
def get_appointments():
    try:
        user = User.query.get(session['user_id'])
        
        # Get query parameters for filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        clinician_id = request.args.get('clinician_id')
        patient_id = request.args.get('patient_id')
        
        # Base query
        query = Appointment.query
        
        # Role-based filtering
        if user.role == 'Clinician':
            # Clinicians can only see their own appointments
            query = query.filter_by(clinician_id=user.id)
        elif clinician_id and user.role == 'Admin':
            # Admins can filter by clinician
            query = query.filter_by(clinician_id=clinician_id)
        
        # Date range filtering
        if start_date:
            start_dt = dateutil.parser.parse(start_date)
            query = query.filter(Appointment.start_time >= start_dt)
        
        if end_date:
            end_dt = dateutil.parser.parse(end_date)
            query = query.filter(Appointment.end_time <= end_dt)
        
        # Patient filtering
        if patient_id:
            query = query.filter_by(patient_id=patient_id)
        
        appointments = query.order_by(Appointment.start_time).all()
        return jsonify([appointment.to_dict() for appointment in appointments])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@appointment_bp.route('/appointments', methods=['POST'])
@login_required
def create_appointment():
    try:
        data = request.json
        user = User.query.get(session['user_id'])
        
        # Validate required fields
        required_fields = ['patient_id', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400
        
        # Parse datetime strings
        start_time = dateutil.parser.parse(data['start_time'])
        end_time = dateutil.parser.parse(data['end_time'])
        
        # Validate appointment times
        if start_time >= end_time:
            return jsonify({'error': 'Start time must be before end time'}), 400
        
        # Set clinician_id based on role
        if user.role == 'Admin' and 'clinician_id' in data:
            clinician_id = data['clinician_id']
        else:
            clinician_id = user.id
        
        appointment = Appointment(
            patient_id=data['patient_id'],
            clinician_id=clinician_id,
            start_time=start_time,
            end_time=end_time,
            appointment_type=data.get('appointment_type', 'individual'),
            notes=data.get('notes', ''),
            recurrence_pattern=data.get('recurrence_pattern'),
            recurrence_end_date=dateutil.parser.parse(data['recurrence_end_date']) if data.get('recurrence_end_date') else None
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        # Handle recurring appointments
        if appointment.recurrence_pattern and appointment.recurrence_end_date:
            create_recurring_appointments(appointment)
        
        return jsonify(appointment.to_dict()), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

def create_recurring_appointments(base_appointment):
    """Create recurring appointments based on the pattern"""
    try:
        current_date = base_appointment.start_time
        end_date = base_appointment.recurrence_end_date
        pattern = base_appointment.recurrence_pattern
        
        # Calculate interval based on pattern
        if pattern == 'daily':
            interval = timedelta(days=1)
        elif pattern == 'weekly':
            interval = timedelta(weeks=1)
        elif pattern == 'monthly':
            interval = timedelta(days=30)  # Approximate monthly
        else:
            return
        
        duration = base_appointment.end_time - base_appointment.start_time
        
        while current_date + interval <= end_date:
            current_date += interval
            
            recurring_appointment = Appointment(
                patient_id=base_appointment.patient_id,
                clinician_id=base_appointment.clinician_id,
                start_time=current_date,
                end_time=current_date + duration,
                appointment_type=base_appointment.appointment_type,
                notes=base_appointment.notes,
                recurrence_pattern=base_appointment.recurrence_pattern
            )
            
            db.session.add(recurring_appointment)
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise e

@appointment_bp.route('/appointments/<int:appointment_id>', methods=['GET'])
@login_required
def get_appointment(appointment_id):
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        user = User.query.get(session['user_id'])
        
        # Check permissions
        if user.role == 'Clinician' and appointment.clinician_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify(appointment.to_dict())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@appointment_bp.route('/appointments/<int:appointment_id>', methods=['PUT'])
@login_required
def update_appointment(appointment_id):
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        user = User.query.get(session['user_id'])
        data = request.json
        
        # Check permissions
        if user.role == 'Clinician' and appointment.clinician_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Update appointment fields
        if 'start_time' in data:
            appointment.start_time = dateutil.parser.parse(data['start_time'])
        
        if 'end_time' in data:
            appointment.end_time = dateutil.parser.parse(data['end_time'])
        
        if 'status' in data:
            appointment.status = data['status']
        
        if 'notes' in data:
            appointment.notes = data['notes']
        
        if 'appointment_type' in data:
            appointment.appointment_type = data['appointment_type']
        
        # Only admins can change clinician assignment
        if user.role == 'Admin' and 'clinician_id' in data:
            appointment.clinician_id = data['clinician_id']
        
        db.session.commit()
        return jsonify(appointment.to_dict())
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@appointment_bp.route('/appointments/<int:appointment_id>', methods=['DELETE'])
@login_required
def delete_appointment(appointment_id):
    try:
        appointment = Appointment.query.get_or_404(appointment_id)
        user = User.query.get(session['user_id'])
        
        # Check permissions
        if user.role == 'Clinician' and appointment.clinician_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        db.session.delete(appointment)
        db.session.commit()
        return '', 204
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@appointment_bp.route('/clinicians/<int:clinician_id>/schedule', methods=['GET'])
@login_required
def get_clinician_schedule(clinician_id):
    try:
        user = User.query.get(session['user_id'])
        
        # Check permissions - clinicians can only view their own schedule
        if user.role == 'Clinician' and user.id != clinician_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get date range from query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Appointment.query.filter_by(clinician_id=clinician_id)
        
        if start_date:
            start_dt = dateutil.parser.parse(start_date)
            query = query.filter(Appointment.start_time >= start_dt)
        
        if end_date:
            end_dt = dateutil.parser.parse(end_date)
            query = query.filter(Appointment.end_time <= end_dt)
        
        appointments = query.order_by(Appointment.start_time).all()
        return jsonify([appointment.to_dict() for appointment in appointments])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

