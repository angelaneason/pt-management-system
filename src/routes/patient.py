"""
Patient routes for the multi-tenant Physical Therapy Management System.

This module handles all patient-related API endpoints within tenant contexts.
"""

from flask import Blueprint, jsonify, request, g
from src.models.patient import Patient
from src.models.client import Client
from src.models.public import db
from src.middleware.tenant import tenant_required, log_tenant_action, get_current_user_profile
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

# Create blueprint with tenant-aware URL prefix
patient_bp = Blueprint('patient', __name__, url_prefix='/api/v1/tenants/<tenant_slug>')

@patient_bp.route('/patients', methods=['GET'])
@tenant_required
def get_patients(tenant_slug):
    """
    Get all patients for the current tenant.
    
    Query parameters:
    - status: Filter by patient status (Active, Discharged, On Hold)
    - client_id: Filter by client ID
    - search: Search in patient names
    - page: Page number for pagination
    - per_page: Items per page (default 50, max 100)
    """
    try:
        query = Patient.query.filter_by(is_active=True)
        
        # Apply filters
        status = request.args.get('status')
        if status:
            query = query.filter_by(status=status)
        
        client_id = request.args.get('client_id')
        if client_id:
            query = query.filter_by(client_id=client_id)
        
        search = request.args.get('search')
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Patient.first_name.ilike(search_term)) |
                (Patient.last_name.ilike(search_term)) |
                (Patient.medical_record_number.ilike(search_term))
            )
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 100)
        
        patients_paginated = query.order_by(Patient.last_name, Patient.first_name).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Include relationships if requested
        include_relationships = request.args.get('include_relationships', 'false').lower() == 'true'
        
        patients_data = [
            patient.to_dict(include_relationships=include_relationships) 
            for patient in patients_paginated.items
        ]
        
        log_tenant_action('view', 'patients', description=f"Viewed patients list (page {page})")
        
        return jsonify({
            'patients': patients_data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': patients_paginated.total,
                'pages': patients_paginated.pages,
                'has_next': patients_paginated.has_next,
                'has_prev': patients_paginated.has_prev
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting patients: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@patient_bp.route('/patients', methods=['POST'])
@tenant_required
def create_patient(tenant_slug):
    """
    Create a new patient in the current tenant.
    
    Expected JSON payload with patient information including demographics,
    medical information, insurance details, etc.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Validate client_id if provided
        if data.get('client_id'):
            client = Client.query.get(data['client_id'])
            if not client or not client.is_active:
                return jsonify({'error': 'Invalid client ID'}), 400
        
        # Validate date fields
        date_fields = ['date_of_birth', 'therapy_start_date', 'therapy_end_date', 'discharge_date']
        for field in date_fields:
            if data.get(field):
                try:
                    datetime.strptime(data[field], '%Y-%m-%d').date()
                except ValueError:
                    return jsonify({'error': f'Invalid date format for {field}. Use YYYY-MM-DD'}), 400
        
        # Create patient
        patient = Patient(
            first_name=data['first_name'],
            last_name=data['last_name'],
            middle_name=data.get('middle_name'),
            preferred_name=data.get('preferred_name'),
            medical_record_number=data.get('medical_record_number'),
            ssn_last_four=data.get('ssn_last_four'),
            date_of_birth=datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date() if data.get('date_of_birth') else None,
            gender=data.get('gender'),
            email=data.get('email'),
            phone_primary=data.get('phone_primary'),
            phone_secondary=data.get('phone_secondary'),
            preferred_contact_method=data.get('preferred_contact_method', 'Phone'),
            address_line1=data.get('address_line1'),
            address_line2=data.get('address_line2'),
            city=data.get('city'),
            state=data.get('state'),
            zip_code=data.get('zip_code'),
            country=data.get('country', 'USA'),
            emergency_contact_name=data.get('emergency_contact_name'),
            emergency_contact_relationship=data.get('emergency_contact_relationship'),
            emergency_contact_phone=data.get('emergency_contact_phone'),
            primary_insurance=data.get('primary_insurance'),
            primary_insurance_id=data.get('primary_insurance_id'),
            primary_insurance_group=data.get('primary_insurance_group'),
            secondary_insurance=data.get('secondary_insurance'),
            secondary_insurance_id=data.get('secondary_insurance_id'),
            primary_diagnosis=data.get('primary_diagnosis'),
            secondary_diagnoses=data.get('secondary_diagnoses'),
            icd10_codes=data.get('icd10_codes'),
            referring_physician=data.get('referring_physician'),
            referring_physician_npi=data.get('referring_physician_npi'),
            therapy_start_date=datetime.strptime(data['therapy_start_date'], '%Y-%m-%d').date() if data.get('therapy_start_date') else None,
            therapy_end_date=datetime.strptime(data['therapy_end_date'], '%Y-%m-%d').date() if data.get('therapy_end_date') else None,
            frequency_per_week=data.get('frequency_per_week', 2),
            total_visits_authorized=data.get('total_visits_authorized'),
            chief_complaint=data.get('chief_complaint'),
            medical_history=data.get('medical_history'),
            surgical_history=data.get('surgical_history'),
            medications=data.get('medications'),
            allergies=data.get('allergies'),
            precautions=data.get('precautions'),
            contraindications=data.get('contraindications'),
            functional_limitations=data.get('functional_limitations'),
            goals_short_term=data.get('goals_short_term'),
            goals_long_term=data.get('goals_long_term'),
            prior_level_of_function=data.get('prior_level_of_function'),
            initial_pain_score=data.get('initial_pain_score'),
            current_pain_score=data.get('current_pain_score'),
            outcome_measures=data.get('outcome_measures'),
            client_id=data.get('client_id'),
            primary_therapist_id=data.get('primary_therapist_id'),
            care_team=data.get('care_team'),
            preferred_appointment_days=data.get('preferred_appointment_days'),
            preferred_appointment_times=data.get('preferred_appointment_times'),
            scheduling_notes=data.get('scheduling_notes'),
            language_preference=data.get('language_preference', 'English'),
            interpreter_needed=data.get('interpreter_needed', False),
            communication_notes=data.get('communication_notes'),
            copay_amount=data.get('copay_amount'),
            deductible_met=data.get('deductible_met', False),
            financial_responsibility=data.get('financial_responsibility'),
            payment_plan=data.get('payment_plan'),
            status=data.get('status', 'Active'),
            created_by=g.current_user_id
        )
        
        db.session.add(patient)
        db.session.commit()
        
        log_tenant_action(
            'create', 
            'patient', 
            resource_id=patient.id,
            description=f"Created patient {patient.full_name}",
            new_values=patient.to_dict()
        )
        
        return jsonify(patient.to_dict(include_relationships=True)), 201
        
    except Exception as e:
        logger.error(f"Error creating patient: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@patient_bp.route('/patients/<int:patient_id>', methods=['GET'])
@tenant_required
def get_patient(tenant_slug, patient_id):
    """Get a specific patient by ID."""
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        if not patient.is_active:
            return jsonify({'error': 'Patient not found'}), 404
        
        include_relationships = request.args.get('include_relationships', 'true').lower() == 'true'
        
        log_tenant_action(
            'view', 
            'patient', 
            resource_id=patient.id,
            description=f"Viewed patient {patient.full_name}"
        )
        
        return jsonify(patient.to_dict(include_relationships=include_relationships)), 200
        
    except Exception as e:
        logger.error(f"Error getting patient {patient_id}: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@patient_bp.route('/patients/<int:patient_id>', methods=['PUT'])
@tenant_required
def update_patient(tenant_slug, patient_id):
    """Update a specific patient."""
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        if not patient.is_active:
            return jsonify({'error': 'Patient not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Store old values for audit log
        old_values = patient.to_dict()
        
        # Update fields
        updatable_fields = [
            'first_name', 'last_name', 'middle_name', 'preferred_name',
            'medical_record_number', 'ssn_last_four', 'gender',
            'email', 'phone_primary', 'phone_secondary', 'preferred_contact_method',
            'address_line1', 'address_line2', 'city', 'state', 'zip_code', 'country',
            'emergency_contact_name', 'emergency_contact_relationship', 'emergency_contact_phone',
            'primary_insurance', 'primary_insurance_id', 'primary_insurance_group',
            'secondary_insurance', 'secondary_insurance_id',
            'primary_diagnosis', 'secondary_diagnoses', 'icd10_codes',
            'referring_physician', 'referring_physician_npi',
            'frequency_per_week', 'total_visits_authorized',
            'chief_complaint', 'medical_history', 'surgical_history',
            'medications', 'allergies', 'precautions', 'contraindications',
            'functional_limitations', 'goals_short_term', 'goals_long_term',
            'prior_level_of_function', 'current_pain_score', 'outcome_measures',
            'client_id', 'primary_therapist_id', 'care_team',
            'preferred_appointment_days', 'preferred_appointment_times', 'scheduling_notes',
            'language_preference', 'interpreter_needed', 'communication_notes',
            'copay_amount', 'deductible_met', 'financial_responsibility', 'payment_plan',
            'status', 'discharge_reason', 'discharge_summary',
            'satisfaction_score', 'outcome_achieved', 'readmission_risk'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(patient, field, data[field])
        
        # Handle date fields
        date_fields = ['date_of_birth', 'therapy_start_date', 'therapy_end_date', 'discharge_date']
        for field in date_fields:
            if field in data and data[field]:
                try:
                    setattr(patient, field, datetime.strptime(data[field], '%Y-%m-%d').date())
                except ValueError:
                    return jsonify({'error': f'Invalid date format for {field}. Use YYYY-MM-DD'}), 400
            elif field in data and data[field] is None:
                setattr(patient, field, None)
        
        # Update visit counts if needed
        if 'total_visits_authorized' in data:
            patient.update_visit_counts()
        
        patient.updated_at = datetime.utcnow()
        db.session.commit()
        
        log_tenant_action(
            'update', 
            'patient', 
            resource_id=patient.id,
            description=f"Updated patient {patient.full_name}",
            old_values=old_values,
            new_values=patient.to_dict()
        )
        
        return jsonify(patient.to_dict(include_relationships=True)), 200
        
    except Exception as e:
        logger.error(f"Error updating patient {patient_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@patient_bp.route('/patients/<int:patient_id>', methods=['DELETE'])
@tenant_required
def delete_patient(tenant_slug, patient_id):
    """Soft delete a patient (mark as inactive)."""
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        if not patient.is_active:
            return jsonify({'error': 'Patient not found'}), 404
        
        # Soft delete
        patient.is_active = False
        patient.updated_at = datetime.utcnow()
        db.session.commit()
        
        log_tenant_action(
            'delete', 
            'patient', 
            resource_id=patient.id,
            description=f"Deleted patient {patient.full_name}"
        )
        
        return jsonify({'message': 'Patient deleted successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting patient {patient_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@patient_bp.route('/patients/<int:patient_id>/discharge', methods=['POST'])
@tenant_required
def discharge_patient(tenant_slug, patient_id):
    """
    Discharge a patient.
    
    Expected JSON payload:
    {
        "discharge_date": "2024-01-15",
        "discharge_reason": "Goals met",
        "discharge_summary": "Patient has achieved all therapy goals...",
        "outcome_achieved": true,
        "satisfaction_score": 5
    }
    """
    try:
        patient = Patient.query.get_or_404(patient_id)
        
        if not patient.is_active:
            return jsonify({'error': 'Patient not found'}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update discharge information
        if data.get('discharge_date'):
            try:
                patient.discharge_date = datetime.strptime(data['discharge_date'], '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid discharge date format. Use YYYY-MM-DD'}), 400
        else:
            patient.discharge_date = date.today()
        
        patient.discharge_reason = data.get('discharge_reason')
        patient.discharge_summary = data.get('discharge_summary')
        patient.outcome_achieved = data.get('outcome_achieved')
        patient.satisfaction_score = data.get('satisfaction_score')
        patient.status = 'Discharged'
        patient.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        log_tenant_action(
            'discharge', 
            'patient', 
            resource_id=patient.id,
            description=f"Discharged patient {patient.full_name}",
            new_values={
                'discharge_date': patient.discharge_date.isoformat() if patient.discharge_date else None,
                'discharge_reason': patient.discharge_reason,
                'status': patient.status
            }
        )
        
        return jsonify({
            'message': 'Patient discharged successfully',
            'patient': patient.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error discharging patient {patient_id}: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


# Error handlers for the blueprint
@patient_bp.errorhandler(404)
def handle_not_found(error):
    return jsonify({'error': 'Patient not found'}), 404


@patient_bp.errorhandler(400)
def handle_bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400

