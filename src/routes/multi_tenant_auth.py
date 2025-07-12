"""
Multi-tenant authentication routes for the Physical Therapy Management System.

This module handles authentication, company management, and user registration
for the multi-tenant architecture.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import check_password_hash
from datetime import datetime, timedelta
from src.models.public import db, User, Company, CompanyUser, Practice
from src.utils.database import DatabaseManager
from src.middleware.tenant import public_route, log_tenant_action
import re
import logging

logger = logging.getLogger(__name__)

# Create blueprint for multi-tenant auth routes
mt_auth_bp = Blueprint('mt_auth', __name__, url_prefix='/api/v1')

@mt_auth_bp.route('/auth/login', methods=['POST'])
@public_route
def login():
    """
    Authenticate user and return access token with company information.
    
    Expected JSON payload:
    {
        "username": "user@example.com",
        "password": "password123",
        "company_slug": "optional_company_slug"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        username = data.get('username')
        password = data.get('password')
        company_slug = data.get('company_slug')
        
        if not username or not password:
            return jsonify({'error': 'Username and password required'}), 400
        
        # Find user by username or email
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 401
        
        if user.is_locked():
            return jsonify({'error': 'Account is locked due to failed login attempts'}), 401
        
        # Get user's companies
        user_companies = CompanyUser.query.filter_by(
            user_id=user.id,
            is_active=True
        ).join(Company).filter(Company.is_active == True).all()
        
        if not user_companies:
            return jsonify({'error': 'No active company access found'}), 403
        
        # If company_slug is provided, validate access
        selected_company = None
        if company_slug:
            selected_company = next(
                (cu for cu in user_companies if cu.company.slug == company_slug),
                None
            )
            if not selected_company:
                return jsonify({'error': f'No access to company "{company_slug}"'}), 403
        else:
            # Use the first company if none specified
            selected_company = user_companies[0]
        
        # Update user login information
        user.last_login = datetime.utcnow()
        user.failed_login_attempts = 0
        user.locked_until = None
        
        # Update company user last access
        selected_company.last_access = datetime.utcnow()
        if not selected_company.joined_at:
            selected_company.joined_at = datetime.utcnow()
        
        db.session.commit()
        
        # Create JWT token with company information
        additional_claims = {
            'tenant': selected_company.company.slug,
            'company_id': selected_company.company.id,
            'role': selected_company.role,
            'permissions': selected_company.permissions or {}
        }
        
        access_token = create_access_token(
            identity=user.id,
            additional_claims=additional_claims,
            expires_delta=timedelta(hours=24)
        )
        
        # Prepare response
        companies_data = []
        for cu in user_companies:
            companies_data.append({
                'id': cu.company.id,
                'name': cu.company.name,
                'slug': cu.company.slug,
                'role': cu.role,
                'permissions': cu.permissions,
                'is_current': cu.company.slug == selected_company.company.slug
            })
        
        return jsonify({
            'access_token': access_token,
            'user': user.to_dict(),
            'current_company': selected_company.company.to_dict(),
            'current_role': selected_company.role,
            'companies': companies_data,
            'permissions': selected_company.permissions or {}
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@mt_auth_bp.route('/auth/switch-company', methods=['POST'])
@jwt_required()
@public_route
def switch_company():
    """
    Switch to a different company context for the current user.
    
    Expected JSON payload:
    {
        "company_slug": "new_company_slug"
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or 'company_slug' not in data:
            return jsonify({'error': 'Company slug required'}), 400
        
        company_slug = data['company_slug']
        
        # Validate user access to the company
        company_user = CompanyUser.query.join(Company).filter(
            CompanyUser.user_id == user_id,
            Company.slug == company_slug,
            CompanyUser.is_active == True,
            Company.is_active == True
        ).first()
        
        if not company_user:
            return jsonify({'error': f'No access to company "{company_slug}"'}), 403
        
        # Update last access
        company_user.last_access = datetime.utcnow()
        db.session.commit()
        
        # Create new JWT token with updated company information
        additional_claims = {
            'tenant': company_user.company.slug,
            'company_id': company_user.company.id,
            'role': company_user.role,
            'permissions': company_user.permissions or {}
        }
        
        access_token = create_access_token(
            identity=user_id,
            additional_claims=additional_claims,
            expires_delta=timedelta(hours=24)
        )
        
        return jsonify({
            'access_token': access_token,
            'current_company': company_user.company.to_dict(),
            'current_role': company_user.role,
            'permissions': company_user.permissions or {}
        }), 200
        
    except Exception as e:
        logger.error(f"Switch company error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@mt_auth_bp.route('/auth/register', methods=['POST'])
@public_route
def register():
    """
    Register a new user and optionally create a new company.
    
    Expected JSON payload:
    {
        "username": "johndoe",
        "email": "john@example.com",
        "password": "password123",
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+1234567890",
        "company": {
            "name": "ABC Physical Therapy",
            "slug": "abc-pt",  // optional, will be generated if not provided
            "description": "A leading physical therapy practice",
            "email": "info@abcpt.com",
            "phone": "+1234567890",
            "address": "123 Main St, City, State 12345"
        }
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['username', 'email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == data['username']) | (User.email == data['email'])
        ).first()
        
        if existing_user:
            return jsonify({'error': 'User with this username or email already exists'}), 409
        
        # Validate company data if provided
        company_data = data.get('company')
        if company_data:
            if not company_data.get('name'):
                return jsonify({'error': 'Company name is required'}), 400
            
            # Generate slug if not provided
            if not company_data.get('slug'):
                company_slug = generate_company_slug(company_data['name'])
            else:
                company_slug = company_data['slug']
            
            # Validate slug format
            if not is_valid_slug(company_slug):
                return jsonify({'error': 'Invalid company slug format'}), 400
            
            # Check if company slug already exists
            existing_company = Company.query.filter_by(slug=company_slug).first()
            if existing_company:
                return jsonify({'error': f'Company slug "{company_slug}" already exists'}), 409
        
        # Create user
        user = User(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            is_verified=False  # Email verification would be implemented separately
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.flush()  # Get user ID
        
        # Create company if provided
        if company_data:
            company = Company(
                name=company_data['name'],
                slug=company_slug,
                description=company_data.get('description'),
                email=company_data.get('email'),
                phone=company_data.get('phone'),
                address=company_data.get('address'),
                subscription_plan='trial',  # Start with trial
                subscription_status='active'
            )
            
            db.session.add(company)
            db.session.flush()  # Get company ID
            
            # Create company-user relationship with admin role
            company_user = CompanyUser(
                user_id=user.id,
                company_id=company.id,
                role='Company Admin',
                can_manage_users=True,
                can_manage_settings=True,
                can_view_reports=True,
                can_manage_billing=True,
                joined_at=datetime.utcnow()
            )
            
            db.session.add(company_user)
            
            # Create tenant schema for the new company
            db_manager = current_app.extensions.get('database_manager')
            if db_manager:
                schema_created = db_manager.create_tenant_schema(company_slug)
                if not schema_created:
                    db.session.rollback()
                    return jsonify({'error': 'Failed to create company workspace'}), 500
        
        db.session.commit()
        
        # Prepare response
        response_data = {
            'user': user.to_dict(),
            'message': 'User registered successfully'
        }
        
        if company_data:
            response_data['company'] = company.to_dict()
            response_data['message'] = 'User and company registered successfully'
        
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


@mt_auth_bp.route('/companies', methods=['GET'])
@jwt_required()
@public_route
def get_user_companies():
    """Get all companies the current user has access to."""
    try:
        user_id = get_jwt_identity()
        
        company_users = CompanyUser.query.filter_by(
            user_id=user_id,
            is_active=True
        ).join(Company).filter(Company.is_active == True).all()
        
        companies = []
        for cu in company_users:
            company_data = cu.company.to_dict()
            company_data['role'] = cu.role
            company_data['permissions'] = cu.permissions
            company_data['joined_at'] = cu.joined_at.isoformat() if cu.joined_at else None
            company_data['last_access'] = cu.last_access.isoformat() if cu.last_access else None
            companies.append(company_data)
        
        return jsonify({'companies': companies}), 200
        
    except Exception as e:
        logger.error(f"Get companies error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@mt_auth_bp.route('/companies', methods=['POST'])
@jwt_required()
@public_route
def create_company():
    """
    Create a new company (requires appropriate permissions).
    
    Expected JSON payload:
    {
        "name": "New Physical Therapy Clinic",
        "slug": "new-pt-clinic",  // optional
        "description": "Description of the clinic",
        "email": "info@newptclinic.com",
        "phone": "+1234567890",
        "address": "456 Oak St, City, State 12345"
    }
    """
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data or not data.get('name'):
            return jsonify({'error': 'Company name is required'}), 400
        
        # Generate slug if not provided
        if not data.get('slug'):
            company_slug = generate_company_slug(data['name'])
        else:
            company_slug = data['slug']
        
        # Validate slug format
        if not is_valid_slug(company_slug):
            return jsonify({'error': 'Invalid company slug format'}), 400
        
        # Check if company slug already exists
        existing_company = Company.query.filter_by(slug=company_slug).first()
        if existing_company:
            return jsonify({'error': f'Company slug "{company_slug}" already exists'}), 409
        
        # Create company
        company = Company(
            name=data['name'],
            slug=company_slug,
            description=data.get('description'),
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            subscription_plan='trial',
            subscription_status='active'
        )
        
        db.session.add(company)
        db.session.flush()
        
        # Create company-user relationship with admin role
        company_user = CompanyUser(
            user_id=user_id,
            company_id=company.id,
            role='Company Admin',
            can_manage_users=True,
            can_manage_settings=True,
            can_view_reports=True,
            can_manage_billing=True,
            joined_at=datetime.utcnow()
        )
        
        db.session.add(company_user)
        
        # Create tenant schema
        db_manager = current_app.extensions.get('database_manager')
        if db_manager:
            schema_created = db_manager.create_tenant_schema(company_slug)
            if not schema_created:
                db.session.rollback()
                return jsonify({'error': 'Failed to create company workspace'}), 500
        
        db.session.commit()
        
        return jsonify({
            'company': company.to_dict(),
            'role': company_user.role,
            'message': 'Company created successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Create company error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Internal server error'}), 500


def generate_company_slug(company_name):
    """
    Generate a URL-friendly slug from company name.
    
    Args:
        company_name (str): Company name
        
    Returns:
        str: Generated slug
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = company_name.lower().strip()
    # Remove special characters except hyphens and alphanumeric
    slug = re.sub(r'[^a-z0-9\-\s]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'\s+', '-', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    # Ensure uniqueness by appending number if needed
    base_slug = slug
    counter = 1
    while Company.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug


def is_valid_slug(slug):
    """
    Validate slug format.
    
    Args:
        slug (str): Slug to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not slug or len(slug) < 2 or len(slug) > 50:
        return False
    
    # Must contain only lowercase letters, numbers, and hyphens
    # Cannot start or end with hyphen
    pattern = r'^[a-z0-9]([a-z0-9\-]*[a-z0-9])?$'
    return bool(re.match(pattern, slug))


# Error handlers for the blueprint
@mt_auth_bp.errorhandler(400)
def handle_bad_request(error):
    return jsonify({'error': 'Bad request', 'message': str(error)}), 400


@mt_auth_bp.errorhandler(401)
def handle_unauthorized(error):
    return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401


@mt_auth_bp.errorhandler(403)
def handle_forbidden(error):
    return jsonify({'error': 'Forbidden', 'message': 'Access denied'}), 403


@mt_auth_bp.errorhandler(409)
def handle_conflict(error):
    return jsonify({'error': 'Conflict', 'message': str(error)}), 409

